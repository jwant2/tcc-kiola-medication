from drf_yasg import openapi

compound_minor = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Compound ID of this Adverse reaction item",
        ),
        "name": openapi.Schema(type=openapi.TYPE_STRING, description="Compound name"),
    },
)


compound_res = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "id": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="id of  compound / medication product",
            ),
            "name": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="name of  compound / medication product",
            ),
            "source": openapi.Schema(
                type=openapi.TYPE_STRING, description="name of  compound source"
            ),
            "activeComponents": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_STRING, description="name of activeComponent"
                ),
                description="activeComponent name",
            ),
            "formulation": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="dosage form of compound - Tablet/Capsule/Solution/etc.",
            ),
        },
    ),
)

adverse_reaction_res = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "id": openapi.Schema(
                type=openapi.TYPE_STRING, description="Medication Adverse Reaction id"
            ),
            "compound": compound_minor,
            "reactionType": openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=[
                    "Allergy",
                    "Side Effect",
                    "Intolerance",
                    "Idiosyncratic",
                    "Unknown",
                ],
                description="Type of adverse reaction",
            ),
            "reactions": openapi.Schema(
                type=openapi.TYPE_STRING, description="reaction details"
            ),
            "createdAt": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="created time of this reaction item  ",
                read_only=True,
            ),
            "updatedAt": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="updated time of this reaction item ",
                read_only=True,
            ),
            "active": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Status of this reaction item - false indicates deleted",
            ),
        },
    ),
)


adverse_reaction_req = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["medicationId", "reactionType", "reactions"],
    properties={
        "medicationId": openapi.Schema(
            type=openapi.TYPE_STRING, description="Prescription Id"
        ),
        "reactionType": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["Allergy", "Side Effect", "Intolerance", "Idiosyncratic", "Unknown"],
            description="Type of adverse reaction",
        ),
        "reactions": openapi.Schema(
            type=openapi.TYPE_STRING, description="reaction details"
        ),
        "active": openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description="Status of this reaction item - false indicates deleted",
        ),
    },
    description="Schedule item of taking ",
)

compound_active_compounents = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Compound ID of this Adverse reaction item",
        ),
        "name": openapi.Schema(type=openapi.TYPE_STRING, description="Compound name"),
        "activeComponents": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_STRING, description="name of activeComponent"
            ),
            description="activeComponent name",
        ),
    },
)

prescr_res = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "id": openapi.Schema(
                type=openapi.TYPE_STRING, description="Prescription Id"
            ),
            "reason": openapi.Schema(
                type=openapi.TYPE_STRING, description="Taking reason for prescription"
            ),
            "hint": openapi.Schema(
                type=openapi.TYPE_STRING, description="Taking hint for prescription"
            ),
            "compound": compound_active_compounents,
            "formulation": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="dosage form of compound - Tablet/Capsule/Solution/etc.",
            ),
            "schedules": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Taking Id"
                        ),
                        "display": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Taking details"
                        ),
                    },
                    description="Taking item",
                ),
                description="Takings of prescription",
            ),
            "startDate": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Start time string of prescription",
            ),
            "endDate": openapi.Schema(
                type=openapi.TYPE_STRING, description="End time string of prescription"
            ),
        },
    ),
)

prescr_req = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["compoundName", "medicationType", "startDate"],
    properties={
        "compoundName": openapi.Schema(
            type=openapi.TYPE_STRING, description="Compound Nane"
        ),
        "reason": openapi.Schema(
            type=openapi.TYPE_STRING, description="Reason of taking compound"
        ),
        "hint": openapi.Schema(
            type=openapi.TYPE_STRING, description="Hint of taking compound"
        ),
        "medicationType": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["PRN", "Regular"],
            description="medicationType - PRN/Regular",
        ),
        "startDate": openapi.Schema(
            type=openapi.TYPE_STRING, description="Start time string of prescription"
        ),
        "endDate": openapi.Schema(
            type=openapi.TYPE_STRING, description="End time string of prescription"
        ),
    },
)


taking_props = {
    "id": openapi.Schema(
        type=openapi.TYPE_STRING, read_only=True, description="Schedule/Taking Id"
    ),
    "medicationId": openapi.Schema(
        type=openapi.TYPE_STRING, description="Prescription Id"
    ),
    "strength": openapi.Schema(
        type=openapi.TYPE_STRING,
        description="strength of compound / medication product",
    ),
    "dosage": openapi.Schema(type=openapi.TYPE_STRING, description="dosage of taking"),
    "formulation": openapi.Schema(
        type=openapi.TYPE_STRING, description="formulation of compound"
    ),
    "startDate": openapi.Schema(
        type=openapi.TYPE_STRING, description="start date of taking"
    ),
    "endDate": openapi.Schema(
        type=openapi.TYPE_STRING, description="end date of taking"
    ),
    "frequency": openapi.Schema(
        type=openapi.TYPE_STRING,
        enum=["daily", "weekly", "fornightly", "monthly", "once-only"],
        description="frequency of taking",
    ),
    "reminder": openapi.Schema(
        type=openapi.TYPE_BOOLEAN, description="should set reminder for taking "
    ),
    "modality": openapi.Schema(
        type=openapi.TYPE_STRING,
        enum=["patient", "clinician", "automate"],
        read_only=True,
        description="whether the last editor of this taking is a clinician ",
    ),
    "type": openapi.Schema(
        type=openapi.TYPE_STRING,
        enum=["solar", "custom"],
        description="schedule type - solar or custom ",
    ),
    "time": openapi.Schema(
        type=openapi.TYPE_STRING,
        description="schedule time - morning/noon/afternoon/night or custom time string ",
    ),
}

taking_res = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(type=openapi.TYPE_OBJECT, properties=taking_props),
)
taking_req = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=[
            "medicationId",
            "strength",
            "dosage",
            "formulation",
            "startDate",
            "frequency",
            "reminder",
            "type",
            "time",
        ],
        properties=taking_props,
    ),
)


user_pref_res = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "data": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="timepoint morning/noon/afternoon/night",
                        ),
                        "actualTime": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="actual time string of the timepoint",
                        ),
                    },
                ),
            ),
        },
        description="user preference config for medication time ",
    ),
)

prescr_history_res = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "time": openapi.Schema(
                type=openapi.TYPE_STRING, description="time of change requested"
            ),
            "changes": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "filed": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="name of the filed changed",
                        ),
                        "old": openapi.Schema(
                            type=openapi.TYPE_STRING, description="value before changed"
                        ),
                        "new": openapi.Schema(
                            type=openapi.TYPE_STRING, description="new value"
                        ),
                    },
                    description="change to fields",
                ),
                description="changes made in a request",
            ),
        },
        description="changes history",
    ),
)
