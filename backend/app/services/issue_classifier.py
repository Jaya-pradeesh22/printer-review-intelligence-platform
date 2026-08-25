ISSUE_KEYWORDS = {

    "PRINT_HEAD": [
        "print head",
        "printhead",
        "head issue",
        "head not detected"
    ],

    "CONNECTIVITY": [
        "wifi",
        "network",
        "disconnect",
        "connection",
        "reset",
        "restart"
    ],

    "PRINT_SPEED": [
        "slow print",
        "printing speed",
        "takes time",
        "slow response",
        "2 minutes"
    ],

    "PRINT_QUALITY": [
        "blurry",
        "faded",
        "ink gaps",
        "unclear",
        "poor quality"
    ],

    "SCANNER": [
        "scanner",
        "scan issue",
        "scanning quality",
        "scan slow"
    ],

    "PAPER_JAM": [
        "paper jam",
        "paper stuck",
        "jammed"
    ],

    "DUPLEX_PRINTING": [
        "duplex",
        "2-sided printing",
        "manual duplex",
        "double side"
    ],

    "INSTALLATION": [
        "installation",
        "setup",
        "technician",
        "install delay"
    ],

    "DEFECTIVE_PRODUCT": [
        "defective",
        "not working",
        "dead",
        "faulty"
    ],

    "CUSTOMER_SUPPORT": [
        "customer care",
        "support",
        "service center",
        "no response",
        "helpdesk"
    ],

    "WARRANTY": [
        "warranty",
        "replacement",
        "return policy"
    ],

    "SOFTWARE_APP": [
        "software",
        "app",
        "hp smart",
        "bug"
    ],

    "HARDWARE_FAILURE": [
        "motherboard",
        "hardware",
        "internal damage"
    ],

    "DELIVERY_LOGISTICS": [
        "delivery",
        "late delivery",
        "logistics",
        "shipment"
    ],

    "SECURITY_PRIVACY": [
        "pan card",
        "otp",
        "security threat",
        "privacy"
    ],

    "NOISE": [
        "noise",
        "sound",
        "loud"
    ],

    "MISLEADING_MARKETING": [
        "misleading",
        "false claim",
        "misselling"
    ]
}


def detect_issue_categories(review_text):

    detected_categories = []

    review_lower = review_text.lower()

    for category, keywords in ISSUE_KEYWORDS.items():

        for keyword in keywords:

            if keyword in review_lower:
                detected_categories.append(category)
                break

    return detected_categories