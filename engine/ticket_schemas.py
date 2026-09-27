"""
SEOJEV: Target Platform Schema Validators for Ticket Exports.

Provides strict JSONSchema validation against actual target platform issue-creation APIs:
1. GitHub REST API v3 Issues Schema (POST /repos/{owner}/{repo}/issues)
2. Jira Cloud REST API Issue Creation Schema (POST /rest/api/2/issue or /rest/api/3/issue)
3. Linear GraphQL IssueCreateInput Schema (mutation IssueCreate($input: IssueCreateInput!))
"""
import re
from typing import Any, Dict, List, Optional, Tuple
import jsonschema


# ---------------------------------------------------------------------------
# 1. GitHub REST API v3 Issue Creation Schema
# Ref: https://docs.github.com/en/rest/issues/issues#create-an-issue
# ---------------------------------------------------------------------------
GITHUB_ISSUE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "GitHub Issue Creation Payload",
    "type": "object",
    "required": ["title"],
    "properties": {
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 1024
        },
        "body": {
            "type": "string"
        },
        "labels": {
            "type": "array",
            "items": {"type": "string"}
        },
        "milestone": {
            "type": ["integer", "null"]
        },
        "assignees": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "additionalProperties": False
}


# ---------------------------------------------------------------------------
# 2. Jira Cloud REST API Issue Creation Schema
# Ref: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-post
# Strictly enforces project key/id, summary, issuetype name/id, priority name/id, labels
# ---------------------------------------------------------------------------
JIRA_ISSUE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Jira Cloud Issue Creation Payload",
    "type": "object",
    "required": ["fields"],
    "properties": {
        "fields": {
            "type": "object",
            "required": ["project", "summary", "issuetype"],
            "properties": {
                "project": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]+$"},
                        "id": {"type": "string", "pattern": "^[0-9]+$"}
                    },
                    "oneOf": [
                        {"required": ["key"]},
                        {"required": ["id"]}
                    ],
                    "additionalProperties": False
                },
                "summary": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255
                },
                "description": {
                    "type": ["string", "object"]
                },
                "issuetype": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "id": {"type": "string", "pattern": "^[0-9]+$"}
                    },
                    "oneOf": [
                        {"required": ["name"]},
                        {"required": ["id"]}
                    ],
                    "additionalProperties": False
                },
                "priority": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "enum": ["Lowest", "Low", "Medium", "High", "Highest"]},
                        "id": {"type": "string", "pattern": "^[0-9]+$"}
                    },
                    "oneOf": [
                        {"required": ["name"]},
                        {"required": ["id"]}
                    ],
                    "additionalProperties": False
                },
                "labels": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": "^[^\\s]+$"  # Jira does not allow spaces in labels
                    }
                }
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": False
}


# ---------------------------------------------------------------------------
# 3. Linear GraphQL IssueCreateInput Schema
# Ref: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
# input IssueCreateInput { title: String!, teamId: String!, description: String, priority: Int, labelIds: [String!] }
# ---------------------------------------------------------------------------
LINEAR_ISSUE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Linear GraphQL IssueCreateInput Payload",
    "type": "object",
    "required": ["title", "teamId"],
    "properties": {
        "teamId": {
            "type": "string",
            "minLength": 1,
            # Linear team ID is either a UUID or team key/slug identifier
            "pattern": r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[A-Za-z0-9_-]+)$"
        },
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 255
        },
        "description": {
            "type": "string"
        },
        "priority": {
            "type": "integer",
            "minimum": 0,
            "maximum": 4,
            "description": "0: No priority, 1: Urgent, 2: High, 3: Medium, 4: Low"
        },
        "labelIds": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "additionalProperties": False
}


def validate_ticket_export(platform: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates an exported payload against the target platform's schema.
    Returns (is_valid, error_message).
    """
    plat = platform.lower().strip()
    if plat == "github":
        schema = GITHUB_ISSUE_SCHEMA
    elif plat == "jira":
        schema = JIRA_ISSUE_SCHEMA
    elif plat == "linear":
        schema = LINEAR_ISSUE_SCHEMA
    elif plat == "markdown":
        return True, None
    else:
        return False, f"Unsupported ticket export platform: {platform}"

    try:
        jsonschema.validate(instance=payload, schema=schema)
        return True, None
    except jsonschema.ValidationError as err:
        return False, f"Schema validation error for {platform}: {err.message} (path: {list(err.path)})"
