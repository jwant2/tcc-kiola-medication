CreateCompoundBody = {
    "type": "object",
    "properties": {
        "activeComponents": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "formulation": {"type": "string"},
        "name": {"type": "string"},
        "medicationType": {"type": "string", "enum": ["PRN", "Regular"]},
    },
    "required": ["activeComponents", "formulation", "name", "medicationType"],
}

CreateMedicationBody = {
    "type": "object",
    "properties": {
        "compound": {"type": "object", "properties": {"id": {"type": "string"}}},
        "reason": {"type": "string"},
        "hint": {"type": "string"},
        "strength": {"type": "string"},
        "medicationDosage": {"type": "string"},
        "medicationType": {"type": "string", "enum": ["PRN", "Regular"]},
        "formulation": {"type": "string"},
        "startDate": {"type": "string"},
        "endDate": {"type": "string"},
    },
    "required": ["compound", "medicationType"],
}

CreateReactionBody = {
    "type": "object",
    "properties": {
        "compound": {"type": "object", "properties": {"id": {"type": "string"}}},
        "reactions": {"type": "string"},
        "reactionType": {
            "type": "string",
            "enum": [
                "Allergy",
                "Side Effect",
                "Intolerance",
                "Idiosyncratic",
                "Unknown",
            ],
        },
    },
    "required": ["compound", "reactions", "reactionType"],
}

CreateScheduleBody = {
    "type": "object",
    "properties": {
        "medicationId": {"type": "string"},
        "formulation": {"type": "string"},
        "dosage": {"type": "string"},
        "strength": {"type": "string"},
        "hint": {"type": "string"},
        "startDate": {"type": "string"},
        "endDate": {"type": "string"},
        "reminder": {"type": "boolean"},
        "frequency": {
            "type": "string",
            "enum": ["daily", "weekly", "fortnightly", "monthly", "once"],
        },
        "type": {"type": "string", "enum": ["solar", "custom"]},
    },
    "if": {"properties": {"type": {"const": "solar"}}},
    "then": {
        "properties": {
            "time": {
                "type": "string",
                "enum": ["morning", "afternoon", "noon", "night"],
            },
        }
    },
    "else": {
        "properties": {
            "time": {"type": "string", "pattern": "^([01][0-9]|2[0-3]):([0-5][0-9])$"}
        }
    },
    "required": [
        "dosage",
        "frequency",
        "medicationId",
        "reminder",
        "startDate",
        "strength",
        "type",
        "time",
    ],
}

UpdateUserPreferenceBody = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "actualTime": {"time": {"type": "string"}},
            "type": {
                "type": "string",
                "enum": ["morning", "afternoon", "noon", "night"],
            },
        },
        "required": ["actualTime", "type"],
    },
    "minItems": 1,
}
