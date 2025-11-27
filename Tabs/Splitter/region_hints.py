"""
Region hint metadata for splitter cues.

Each entry records the preferred vertical bands (expressed in 1/10 inch units
relative to an 11-inch page) where a cue is typically located. The splitter
converts these ranges into page-height fractions at runtime and prioritises
OCR/text extraction within those regions before falling back to broader scans.
"""

REGION_HINTS = [
    # Proposal
    {
        "rule": "Proposal",
        "target": "start.any_cues",
        "pattern": "(?s)\\bPLEASE\\s+FIND\\s+ATTACHED\\s+PREMIUM\\s+INDICATION\\b",
        "bands": [[0.2, 0.4]],
    },
    {
        "rule": "Proposal",
        "target": "start.any_cues",
        "pattern": "(?s)\\bBELOW\\s+IS\\s+A\\s+PREMIUM\\s+AND\\s+FEE\\s+SUMMARY\\b",
        "bands": [[0.2, 0.4]],
    },
    {
        "rule": "Proposal",
        "target": "start.any_cues",
        "pattern": "(?s)\\bPLEASE\\s+FIND\\s+ATTACHED\\s+(THE\\s+)?RENEWAL\\s+QUOTE\\b.*\\bSUMMARY\\s+OF\\s+THE\\s+PROPOSAL\\b",
        "bands": [[0.2, 0.4]],
    },
    {
        "rule": "Proposal",
        "target": "end.first_cue",
        "pattern": "(?s)\\bTHANK\\s+YOU\\s+FOR\\s+YOUR\\s+BUSINESS\\b",
        "bands": [[0.3, 0.5]],
    },
    {
        "rule": "Proposal",
        "target": "end.first_cue",
        "pattern": "(?s)\\bTHIS\\s+QUOTATION\\s+IS\\s+ONLY\\s+A\\s+SUMMARY\\b",
        "bands": [[0.3, 0.5]],
    },
    {
        "rule": "Proposal",
        "target": "end.first_cue",
        "pattern": "(?s)\\bTHIS\\s+SIGNED\\s+PROPOSAL\\s+SHALL\\s+BE\\s+MADE\\s+PART\\b",
        "bands": [[0.4, 0.7]],
    },
    {
        "rule": "Proposal",
        "target": "end.first_cue",
        "pattern": "(?s)\\bTHIS\\s+ACCEPTED\\s+QUOTATION\\s+REPLACES\\s+ANY\\s+INDICATION\\b",
        "bands": [[0.4, 0.7]],
    },

    # Signature Certificate
    {
        "rule": "Signature Certificate",
        "target": "start.any_cues",
        "pattern": "(?s)\\bDOCUMENT\\s+COMPLETION\\s+CERTIFICATE\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "Signature Certificate",
        "target": "start.any_cues",
        "pattern": "(?s)\\bDEALER\\s+POLICY\\s+BIND\\s+PACKAGE\\b",
        "bands": [[0.0, 0.2]],
    },

    # Statement of No Loss
    {
        "rule": "Statement of No Loss",
        "target": "require_any",
        "pattern": "(?s)\\bSTATEMENT\\s+OF\\s+NO\\s+LOSS\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "Statement of No Loss",
        "target": "helpful_cues",
        "pattern": "(?s)\\bI\\s+CERTIFY\\s+THAT\\s+I\\s+AM\\s+NOT\\s+AWARE\\s+OF\\s+ANY\\s+LOSSES\\b",
        "bands": [[0.2, 0.5]],
    },
    {
        "rule": "Statement of No Loss",
        "target": "helpful_cues",
        "pattern": "(?s)\\bCIRCUMSTANCES\\s+THAT\\s+MIGHT\\s+GIVE\\s+RISE\\s+TO\\s+A\\s+CLAIM\\b",
        "bands": [[0.2, 0.5]],
    },
    {
        "rule": "Statement of No Loss",
        "target": "helpful_cues",
        "pattern": "(?s)\\bRECEIPT\\b",
        "bands": [[0.2, 0.5]],
    },
    {
        "rule": "Statement of No Loss",
        "target": "helpful_cues",
        "pattern": "(?s)\\bAMOUNT\\s+RECEIVED\\s+BY\\b",
        "bands": [[0.2, 0.5]],
    },

    # Non-Dealer Application
    {
        "rule": "Non-Dealer Application",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNON[-\\s]+DEALER\\s+APPLICATION\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "Non-Dealer Application",
        "target": "helpful_cues",
        "pattern": "(?s)\\bSMOG\\s+TESTING\\b",
        "bands": [[0.25, 0.35]],
    },
    {
        "rule": "Non-Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER[’'`]S\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.9, 1.0]],
    },
    {
        "rule": "Non-Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bNON[-\\s]+OWNED\\s+AUTO\\s+LIABILITY\\b",
        "bands": [[0.0, 0.225]],
    },
    {
        "rule": "Non-Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bCOMMERCIAL\\s+GENERAL\\s+LIABILITY\\b",
        "bands": [[0.065, 0.25]],
    },

    # Property Application
    {
        "rule": "Property Application",
        "target": "start.any_cues",
        "pattern": "(?s)\\bPROPERTY\\s+SUPPLEMENTAL\\b",
        "bands": [[0.0, 0.16]],
    },
    {
        "rule": "Property Application",
        "target": "start.any_cues",
        "pattern": "(?s)\\bPROPERTY\\s+APPLICATION\\b",
        "bands": [[0.0, 0.16]],
    },
    {
        "rule": "Property Application",
        "target": "require_any",
        "pattern": "(?s)\\bMINIMUM\\s+90\\s*%?\\s+CO[-\\s]+INSURANCE\\b",
        "bands": [[0.15, 0.25]],
    },
    {
        "rule": "Property Application",
        "target": "helpful_cues",
        "pattern": "(?s)\\bMINIMUM\\s+90\\s*%?\\s+CO[-\\s]+INSURANCE\\s+APPLIES\\s+TO\\s+ALL\\s+PROPERTY\\s+COVERAGE\\b",
        "bands": [[0.15, 0.25]],
    },
    {
        "rule": "Property Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bLIST\\s+ALL\\s+PROPERTY\\s*,?\\s+CRIME\\s+AND\\s+INLAND\\s+MARINE\\s+LOSSES\\s+IN\\s+LAST\\s+4\\s+YEARS\\b",
        "bands": [[0.3, 0.5]],
    },
    {
        "rule": "Property Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER[’'`]S\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.9, 1.1]],
    },
    {
        "rule": "Property Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bPROPERTY\\s*,?\\s+CRIME\\s+AND\\s+INLAND\\s+MARINE\\b",
        "bands": [[0.33, 0.5]],
    },

    # Location Page DA
    {
        "rule": "Location Page DA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bLOCATION\\s+INFORMATION\\b",
        "bands": [[0.0, 0.15]],
    },
    {
        "rule": "Location Page DA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCOMPLETE\\s+A\\s+SEPARATE\\s+FORM\\s+FOR\\s+EACH\\s+LOCATION\\b",
        "bands": [[0.0, 0.15]],
    },
    {
        "rule": "Location Page DA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bANSWER\\s+THE\\s+FOLLOWING\\s+QUESTIONS\\s+IF\\s+THERE\\s+IS\\s+A\\s+SERVICE\\s*/\\s*REPAIR\\s+FACILITY\\s+ON\\s+PREMISES\\b",
        "bands": [[0.52, 0.65]],
    },

    # Car Hauler Application
    {
        "rule": "Car Hauler Application",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCAR\\s+HAULER\\s+SUPPLEMENTAL\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "Car Hauler Application",
        "target": "helpful_cues",
        "pattern": "(?s)\\bATTACH\\s+PHOTO\\s+OF\\s+EACH\\s+HAULER\\s+TO\\s+SUBMISSION\\b",
        "bands": [[0.13, 0.24]],
    },

    # Physician Statement
    {
        "rule": "Physician Statement",
        "target": "start.any_cues",
        "pattern": "(?s)\\bPHYSICIAN[’'`]S\\s+STATEMENT\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "Physician Statement",
        "target": "helpful_cues",
        "pattern": "(?s)\\bMENTAL\\s+CONDITION\\b",
        "bands": [[0.32, 0.46]],
    },

    # Cyber Application
    {
        "rule": "Cyber Application",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCYBER\\s+LIABILITY\\s+PROGRAM\\s+ENROLLMENT\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "Cyber Application",
        "target": "helpful_cues",
        "pattern": "(?s)\\bCYBER\\s+LIABILITY\\s+PROGRAM\\s+DETAILS\\b",
        "bands": [[0.27, 0.39]],
    },

    # Theft Exclusion
    {
        "rule": "Theft Exclusion",
        "target": "require_any",
        "pattern": "(?s)\\bTHEFT\\s+EXCLUSION\\b",
        "bands": [[0.1, 0.3]],
    },
    {
        "rule": "Theft Exclusion",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.1, 0.3]],
    },
    {
        "rule": "Theft Exclusion",
        "target": "helpful_cues",
        "pattern": "(?s)\\bPLEASE\\s+READ\\s+IT\\s+CAREFULLY\\b",
        "bands": [[0.1, 0.3]],
    },

    # Limited Named Driver Exclusion - Florida
    {
        "rule": "Limited Named Driver Exclusion - Florida",
        "target": "require_any",
        "pattern": "(?s)\\bNAMED\\s+DRIVER\\s+EXCLUSION\\b",
        "bands": [[0.1, 0.3]],
    },
    {
        "rule": "Limited Named Driver Exclusion - Florida",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITED\\b",
        "bands": [[0.15, 0.3]],
    },
    {
        "rule": "Limited Named Driver Exclusion - Florida",
        "target": "helpful_cues",
        "pattern": "(?s)\\bFLORIDA\\b",
        "bands": [[0.15, 0.3]],
    },

    # Limited Named Driver Exclusion
    {
        "rule": "Limited Named Driver Exclusion",
        "target": "require_any",
        "pattern": "(?s)\\bNAMED\\s+DRIVER\\s+EXCLUSION\\b",
        "bands": [[0.1, 0.275]],
    },
    {
        "rule": "Limited Named Driver Exclusion",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITED\\b",
        "bands": [[0.1, 0.275]],
    },

    # Named Driver Exclusion - North Carolina
    {
        "rule": "Named Driver Exclusion - North Carolina",
        "target": "require_any",
        "pattern": "(?s)\\bNAMED\\s+DRIVER\\s+EXCLUSION\\b",
        "bands": [[0.1, 0.27]],
    },
    {
        "rule": "Named Driver Exclusion - North Carolina",
        "target": "helpful_cues",
        "pattern": "(?s)\\bNORTH\\s+CAROLINA\\b",
        "bands": [[0.1, 0.27]],
    },

    # Named Driver Exclusion - South Carolina
    {
        "rule": "Named Driver Exclusion - South Carolina",
        "target": "require_any",
        "pattern": "(?s)\\bNAMED\\s+DRIVER\\s+EXCLUSION\\b",
        "bands": [[0.09, 0.245]],
    },
    {
        "rule": "Named Driver Exclusion - South Carolina",
        "target": "helpful_cues",
        "pattern": "(?s)\\bSOUTH\\s+CAROLINA\\b",
        "bands": [[0.1, 0.245]],
    },

    # Named Driver Exclusion - Washington
    {
        "rule": "Named Driver Exclusion - Washington",
        "target": "require_any",
        "pattern": "(?s)\\bNAMED\\s+DRIVER\\s+EXCLUSION\\b",
        "bands": [[0.1, 0.27]],
    },
    {
        "rule": "Named Driver Exclusion - Washington",
        "target": "helpful_cues",
        "pattern": "(?s)\\bWASHINGTON\\b",
        "bands": [[0.1, 0.27]],
    },

    # Named Driver Exclusion
    {
        "rule": "Named Driver Exclusion",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNAMED\\s+DRIVER\\s+EXCLUSION\\b",
        "bands": [[0.1, 0.28]],
    },
    {
        "rule": "Named Driver Exclusion",
        "target": "start.any_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.1, 0.28]],
    },
    {
        "rule": "Named Driver Exclusion",
        "target": "require_any",
        "pattern": "(?s)\\bNAMED\\s+DRIVER\\s+EXCLUSION\\b",
        "bands": [[0.1, 0.28]],
    },
    {
        "rule": "Named Driver Exclusion",
        "target": "require_any",
        "pattern": "(?s)\\bSCHEDULE\\b",
        "bands": [[0.47, 0.58]],
    },
    {
        "rule": "Named Driver Exclusion",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.1, 0.28]],
    },
    {
        "rule": "Named Driver Exclusion",
        "target": "helpful_cues",
        "pattern": "(?s)\\bEXCLUDED\\s+DRIVER\\b",
        "bands": [[0.63, 0.73]],
    },

    # Non-Listed Driver Limitation
    {
        "rule": "Non-Listed Driver Limitation",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNON[-\\s]+LISTED\\s+DRIVER\\s+LIMITATION\\s+ENDORSEMENT\\b",
        "bands": [[0.1, 0.285]],
    },
    {
        "rule": "Non-Listed Driver Limitation",
        "target": "start.any_cues",
        "pattern": "(?s)\\bSCHEDULE\\s+PERMISSIVE\\s+USER(?:\\s+S)?\\b",
        "bands": [[0.1, 0.22]],
    },
    {
        "rule": "Non-Listed Driver Limitation",
        "target": "end.first_cue",
        "pattern": "(?s)\\bSCHEDULE\\s+PERMISSIVE\\s+USER(?:\\s+S)?\\b",
        "bands": [[0.12, 0.26]],
    },

    # Business Exclusion
    {
        "rule": "Business Exclusion",
        "target": "require_any",
        "pattern": "(?s)\\bLOCATIONS\\s+AND\\s+OPERATIONS\\s+NOT\\s+COVERED\\b",
        "bands": [[0.072, 0.22]],
    },

    # Windstorm and Flood Exclusion
    {
        "rule": "Windstorm and Flood Exclusion",
        "target": "start.any_cues",
        "pattern": "(?s)\\bWINDSTORM\\s+AND\\s+FLOOD\\s+EXCLUSION\\b",
        "bands": [[0.0275, 0.22]],
    },
    {
        "rule": "Windstorm and Flood Exclusion",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.0275, 0.22]],
    },
    {
        "rule": "Windstorm and Flood Exclusion",
        "target": "end.first_cue",
        "pattern": "(?s)\\bSIGNATURE\\s+OF\\s+INSURED\\b",
        "bands": [[0.42, 0.55]],
    },

    # Windstorm and Flood Exclusion - Washington
    {
        "rule": "Windstorm and Flood Exclusion - Washington",
        "target": "start.any_cues",
        "pattern": "(?s)(?=.*WASHINGTON).*WINDSTORM\\s+AND\\s+FLOOD\\s+EXCLUSION",
        "bands": [[0.0275, 0.22]],
    },
    {
        "rule": "Windstorm and Flood Exclusion - Washington",
        "target": "require_any",
        "pattern": "(?s)\\bWASHINGTON\\b",
        "bands": [[0.0275, 0.22]],
    },
    {
        "rule": "Windstorm and Flood Exclusion - Washington",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.0275, 0.22]],
    },
    {
        "rule": "Windstorm and Flood Exclusion - Washington",
        "target": "end.first_cue",
        "pattern": "(?s)\\bSIGNATURE\\s+OF\\s+INSURED\\b",
        "bands": [[0.4, 0.55]],
    },

    # Liquefied Petroleum Gases Exclusion
    {
        "rule": "Liquefied Petroleum Gases Exclusion",
        "target": "start.any_cues",
        "pattern": "(?s)\\bLIQUEFIED\\s+PETROLEUM\\s+GASES\\s+EXCLUSION\\b",
        "bands": [[0.08, 0.3]],
    },
    {
        "rule": "Liquefied Petroleum Gases Exclusion",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.06, 0.23]],
    },
    {
        "rule": "Liquefied Petroleum Gases Exclusion",
        "target": "end.first_cue",
        "pattern": "(?s)\\bNAMED\\s+INSUREDS?\\s+SIGNATURE\\b",
        "bands": [[0.31, 0.45]],
    },
    {
        "rule": "Liquefied Petroleum Gases Exclusion",
        "target": "end.first_cue",
        "pattern": "(?s)\\bSIGNATURE\\s+OF\\s+(THE\\s+)?INSURED\\b",
        "bands": [[0.31, 0.45]],
    },
    {
        "rule": "Liquefied Petroleum Gases Exclusion",
        "target": "end.first_cue",
        "pattern": "(?s)\\bINSURED\\s+SIGNATURE\\b",
        "bands": [[0.31, 0.45]],
    },

    # Used Tires Exclusion Endorsement
    {
        "rule": "Used Tires Exclusion Endorsement",
        "target": "start.any_cues",
        "pattern": "(?s)\\bUSED\\s+TIRES?\\s+EXCLUSION\\s+ENDORSEMENT\\b",
        "bands": [[0.07, 0.25]],
    },
    {
        "rule": "Used Tires Exclusion Endorsement",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.07, 0.25]],
    },
    {
        "rule": "Used Tires Exclusion Endorsement",
        "target": "helpful_cues",
        "pattern": "(?s)\\bPLEASE\\s+READ\\s+IT\\s+CAREFULLY\\b",
        "bands": [[0.07, 0.25]],
    },

    # Excess Hazards Coverage NY
    {
        "rule": "Excess Hazards Coverage NY",
        "target": "start.any_cues",
        "pattern": "(?s)\\bEXCLUSION\\s+OR\\s+EXCESS\\s+COVERAGE.*?HAZARDS\\s+OTHERWISE\\s+INSURED\\b",
        "bands": [[0.075, 0.245]],
    },
    {
        "rule": "Excess Hazards Coverage NY",
        "target": "start.any_cues",
        "pattern": "(?s)\\bHAZARDS\\s+OTHERWISE\\s+INSURED.*?EXCLUSION\\s+OR\\s+EXCESS\\s+COVERAGE\\b",
        "bands": [[0.075, 0.245]],
    },
    {
        "rule": "Excess Hazards Coverage NY",
        "target": "start.any_cues",
        "pattern": "(?s)\\bEXCLUSION\\s+OR\\s+EXCESS\\s+COVERAGE\\s*[–-]\\s*HAZARDS\\s+OTHERWISE\\s+INSURED\\b",
        "bands": [[0.075, 0.245]],
    },
    {
        "rule": "Excess Hazards Coverage NY",
        "target": "require_any",
        "pattern": "(?s)\\bSCHEDULE\\b",
        "bands": [[0.48, 0.57]],
    },
    {
        "rule": "Excess Hazards Coverage NY",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.08, 0.18]],
    },
    {
        "rule": "Excess Hazards Coverage NY",
        "target": "helpful_cues",
        "pattern": "(?s)\\bPLEASE\\s+READ\\s+IT\\s+CAREFULLY\\b",
        "bands": [[0.08, 0.18]],
    },

    # Excess Hazards Coverage
    {
        "rule": "Excess Hazards Coverage",
        "target": "start.any_cues",
        "pattern": "(?s)\\bEXCLUSION\\s+OR\\s+EXCESS\\s+COVERAGE.*?HAZARDS\\s+OTHERWISE\\s+INSURED\\b",
        "bands": [[0.06, 0.21]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "start.any_cues",
        "pattern": "(?s)\\bHAZARDS\\s+OTHERWISE\\s+INSURED.*?EXCLUSION\\s+OR\\s+EXCESS\\s+COVERAGE\\b",
        "bands": [[0.06, 0.21]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "start.any_cues",
        "pattern": "(?s)\\bEXCLUSION\\s+OR\\s+EXCESS\\s+COVERAGE\\s*[–-]\\s*HAZARDS\\s+OTHERWISE\\s+INSURED\\b",
        "bands": [[0.06, 0.21]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "require_any",
        "pattern": "(?s)\\bSECTION\\s+I.*?COVERED\\s+AUTOS.*?COVERAGES\\b",
        "bands": [[0.6, 0.9]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "require_any",
        "pattern": "(?s)\\bSECTION\\s+I.*?COVERAGES\\b",
        "bands": [[0.6, 0.9]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "require_any",
        "pattern": "(?s)\\bSECTION\\s+I\\s+COVERED\\s+AUTOS\\b",
        "bands": [[0.6, 0.9]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "require_any",
        "pattern": "(?s)\\bSECTION\\s+I\\s+COVERAGES\\b",
        "bands": [[0.6, 0.9]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "require_any",
        "pattern": "(?s)\\bCOVERED\\s+AUTOS.*?COVERAGES\\b",
        "bands": [[0.6, 0.9]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTHIS\\s+ENDORSEMENT\\s+CHANGES\\s+THE\\s+POLICY\\b",
        "bands": [[0.06, 0.165]],
    },
    {
        "rule": "Excess Hazards Coverage",
        "target": "helpful_cues",
        "pattern": "(?s)\\bPLEASE\\s+READ\\s+IT\\s+CAREFULLY\\b",
        "bands": [[0.06, 0.165]],
    },

    # Dealer Application
    {
        "rule": "Dealer Application",
        "target": "start.any_cues",
        "pattern": "(?s)\\bDEALER\\s+APPLICATION\\b",
        "bands": [[0.0, 0.13]],
    },
    {
        "rule": "Dealer Application",
        "target": "require_any",
        "pattern": "(?s)\\bNEW\\s+BUSINESS\\s+QUOTE\\b",
        "bands": [[0.1, 0.2]],
    },
    {
        "rule": "Dealer Application",
        "target": "require_any",
        "pattern": "(?s)\\bRENEWAL\\s+OF\\s+POL\\b",
        "bands": [[0.12, 0.22]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bINDICATE\\s+INTERESTS\\s+TO\\s+BE\\s+COVERED\\b",
        "bands": [[0.0, 0.18]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bINDICATE.*?INTERESTS.*?COVERED\\b",
        "bands": [[0.0, 0.18]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bINTERESTS\\s+TO\\s+BE\\s+COVERED\\b",
        "bands": [[0.0, 0.18]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT\\s+S\\s+CONSENT\\s+ADVISORY\\s+WARRANTIES\\b",
        "bands": [[0.57, 0.7]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT\\s+CONSENT\\s+ADVISORY\\s+WARRANTIES\\b",
        "bands": [[0.57, 0.7]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT.*?CONSENT.*?ADVISORY.*?WARRANTIES\\b",
        "bands": [[0.57, 0.7]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANTS\\s+CONSENT\\s+ADVISORY\\s+WARRANTIES\\b",
        "bands": [[0.57, 0.7]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bCONSENT.*?ADVISORY.*?WARRANTIES\\b",
        "bands": [[0.57, 0.7]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bADVISORY.*?WARRANTIES\\b",
        "bands": [[0.57, 0.7]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER\\s+S\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER\\s+S\\s+SIGNATURE\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER\\s+SIGNATURE\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKERS\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKERS\\s+SIGNATURE\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER.*?SIGNATURE.*?COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bSIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bSIGNATURE\\s+COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },
    {
        "rule": "Dealer Application",
        "target": "end.first_cue",
        "pattern": "(?s)\\bSIGNATURE.*?COMPLETION\\b",
        "bands": [[0.92, 1.07]],
    },

    # Supplemental Spousal Liability
    {
        "rule": "Supplemental Spousal Liability",
        "target": "require_any",
        "pattern": "(?s)\\bSUPPLEMENTAL\\s+SPOUSAL\\s+LIABILITY\\b",
        "bands": [[0.085, 0.2]],
    },
    {
        "rule": "Supplemental Spousal Liability",
        "target": "helpful_cues",
        "pattern": "(?s)\\bCOVERAGE\\b",
        "bands": [[0.085, 0.2]],
    },
    {
        "rule": "Supplemental Spousal Liability",
        "target": "helpful_cues",
        "pattern": "(?s)\\bNOTICE\\b",
        "bands": [[0.085, 0.2]],
    },

    # Unlicensed Driver Statement
    {
        "rule": "Unlicensed Driver Statement",
        "target": "require_any",
        "pattern": "(?s)\\bUNLICENSED\\s+DRIVER\\s+STATEMENT\\b",
        "bands": [[0.185, 0.265]],
    },
    {
        "rule": "Unlicensed Driver Statement",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNLICENSED\\s+DRIVER\\b",
        "bands": [[0.185, 0.265]],
    },
    {
        "rule": "Unlicensed Driver Statement",
        "target": "helpful_cues",
        "pattern": "(?s)\\bI\\s+UNDERSTAND\\b",
        "bands": [[0.345, 0.423]],
    },

    # Experience Questionnaire
    {
        "rule": "Experience Questionnaire",
        "target": "require_any",
        "pattern": "(?s)\\bEXPERIENCE\\s+QUESTIONNAIRE\\s+BUSINESSES\\s+IN\\s+OPERATION\\s+LESS\\s+THAN\\s+3\\s+YEARS\\b",
        "bands": [[0.0, 0.15]],
    },
    {
        "rule": "Experience Questionnaire",
        "target": "require_any",
        "pattern": "(?s)\\bEXPERIENCE\\s+QUESTIONNAIRE.*?BUSINESSES\\s+IN\\s+OPERATION.*?LESS\\s+THAN\\s+3\\s+YE\\b",
        "bands": [[0.0, 0.15]],
    },
    {
        "rule": "Experience Questionnaire",
        "target": "helpful_cues",
        "pattern": "(?s)\\bEMPLOYMENT\\s+HISTORY\\b",
        "bands": [[0.415, 0.5]],
    },
    {
        "rule": "Experience Questionnaire",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIST\\s+ALL\\s+EMPLOYMENT\\s+IN\\s+THE\\s+LAST\\s+4\\s+YEARS\\b",
        "bands": [[0.415, 0.5]],
    },
    {
        "rule": "Experience Questionnaire",
        "target": "helpful_cues",
        "pattern": "(?s)\\bBEGINNING\\s+WITH\\s+YOUR\\s+CURRENT\\s+OR\\s+MOST\\s+RECENT\\b",
        "bands": [[0.415, 0.5]],
    },

    # SSA AL
    {
        "rule": "SSA AL",
        "target": "start.any_cues",
        "pattern": "(?s)\\bALABAMA\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "SSA AL",
        "target": "start.any_cues",
        "pattern": "(?s)\\bALABAMA.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.2]],
    },
    {
        "rule": "SSA AL",
        "target": "helpful_cues",
        "pattern": "(?s)\\bALABAMA\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.22, 0.32]],
    },
    {
        "rule": "SSA AL",
        "target": "helpful_cues",
        "pattern": "(?s)\\bALABAMA\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.22, 0.32]],
    },
    {
        "rule": "SSA AL",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s+SELECTION\\b",
        "bands": [[0.22, 0.32]],
    },

    # SSA AZ
    {
        "rule": "SSA AZ",
        "target": "start.any_cues",
        "pattern": "(?s)\\bARIZONA\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.14]],
    },
    {
        "rule": "SSA AZ",
        "target": "start.any_cues",
        "pattern": "(?s)\\bARIZONA.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.14]],
    },
    {
        "rule": "SSA AZ",
        "target": "helpful_cues",
        "pattern": "(?s)\\bARIZONA\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.16, 0.238]],
    },
    {
        "rule": "SSA AZ",
        "target": "helpful_cues",
        "pattern": "(?s)\\bARIZONA\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.16, 0.238]],
    },
    {
        "rule": "SSA AZ",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s+SELECTION\\b",
        "bands": [[0.16, 0.238]],
    },

    # SSA CA
    {
        "rule": "SSA CA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCALIFORNIA.*?AUTOMOTIVE\\s+PROGRAM\\s+SPECIALISTS.*?WWW\\s+DMI\\s+INSURANCE\\s+COM.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.165]],
    },
    {
        "rule": "SSA CA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCALIFORNIA\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.165]],
    },
    {
        "rule": "SSA CA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCALIFORNIA.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.165]],
    },
    {
        "rule": "SSA CA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bAUTOMOTIVE\\s+PROGRAM\\s+SPECIALISTS\\b",
        "bands": [[0.0, 0.165]],
    },
    {
        "rule": "SSA CA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bWWW\\s+DMI\\s+INSURANCE\\s+COM\\b",
        "bands": [[0.0, 0.165]],
    },
    {
        "rule": "SSA CA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bDMI\\s+INSURANCE\\b",
        "bands": [[0.0, 0.165]],
    },

    # SSA AR
    {
        "rule": "SSA AR",
        "target": "start.any_cues",
        "pattern": "(?s)\\bARKANSAS\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.135]],
    },
    {
        "rule": "SSA AR",
        "target": "start.any_cues",
        "pattern": "(?s)\\bARKANSAS.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.135]],
    },
    {
        "rule": "SSA AR",
        "target": "helpful_cues",
        "pattern": "(?s)\\bAUTOMOTIVE\\s+PROGRAM\\s+SPECIALISTS\\b",
        "bands": [[0.0, 0.135]],
    },
    {
        "rule": "SSA AR",
        "target": "helpful_cues",
        "pattern": "(?s)\\bWWW\\s+DMI\\s+INSURANCE\\s+COM\\b",
        "bands": [[0.0, 0.135]],
    },
    {
        "rule": "SSA AR",
        "target": "helpful_cues",
        "pattern": "(?s)\\bDMI\\s+INSURANCE\\b",
        "bands": [[0.0, 0.135]],
    },
    {
        "rule": "SSA AR",
        "target": "end.first_cue",
        "pattern": "(?s)\\bINSURED\\s+S\\s+SIGNATURE\\b",
        "bands": [[0.45, 0.615]],
    },
    {
        "rule": "SSA AR",
        "target": "end.first_cue",
        "pattern": "(?s)\\bINSURED\\s+SIGNATURE\\b",
        "bands": [[0.45, 0.615]],
    },

    # SSA CO
    {
        "rule": "SSA CO",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCOLORADO\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.175]],
    },
    {
        "rule": "SSA CO",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCOLORADO.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.175]],
    },
    {
        "rule": "SSA CO",
        "target": "helpful_cues",
        "pattern": "(?s)\\bCOLORADO\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.215, 0.315]],
    },
    {
        "rule": "SSA CO",
        "target": "helpful_cues",
        "pattern": "(?s)\\bCOLORADO\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.215, 0.315]],
    },
    {
        "rule": "SSA CO",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s+SELECTION\\b",
        "bands": [[0.215, 0.315]],
    },

    # SSA GA
    {
        "rule": "SSA GA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bGEORGIA\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.02, 0.161]],
    },
    {
        "rule": "SSA GA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bGEORGIA.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.02, 0.161]],
    },
    {
        "rule": "SSA GA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bGEORGIA\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.21, 0.3]],
    },
    {
        "rule": "SSA GA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bGEORGIA\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.21, 0.3]],
    },
    {
        "rule": "SSA GA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s+SELECTION\\b",
        "bands": [[0.21, 0.3]],
    },

    # SSA ID
    {
        "rule": "SSA ID",
        "target": "start.any_cues",
        "pattern": "(?s)\\bIDAHO\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.161]],
    },
    {
        "rule": "SSA ID",
        "target": "start.any_cues",
        "pattern": "(?s)\\bIDAHO.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.161]],
    },
    {
        "rule": "SSA ID",
        "target": "helpful_cues",
        "pattern": "(?s)\\bIDAHO\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.22, 0.3]],
    },
    {
        "rule": "SSA ID",
        "target": "helpful_cues",
        "pattern": "(?s)\\bIDAHO\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.22, 0.3]],
    },
    {
        "rule": "SSA ID",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s+SELECTION\\b",
        "bands": [[0.22, 0.3]],
    },

    # SSA IL
    {
        "rule": "SSA IL",
        "target": "start.any_cues",
        "pattern": "(?s)\\bILLINOIS\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.02, 0.16]],
    },
    {
        "rule": "SSA IL",
        "target": "start.any_cues",
        "pattern": "(?s)\\bILLINOIS.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.02, 0.16]],
    },
    {
        "rule": "SSA IL",
        "target": "start.any_cues",
        "pattern": "(?s)\\bILLINOIS\\s+UNINSURED\\s+MOTORISTS\\s+COVERAGE\\b",
        "bands": [[0.02, 0.16]],
    },
    {
        "rule": "SSA IL",
        "target": "require_any",
        "pattern": "(?s)\\bILLINOIS\\b",
        "bands": [[0.0, 1.0]],
    },
    {
        "rule": "SSA IL",
        "target": "helpful_cues",
        "pattern": "(?s)\\bSELECTION\\s*\\*/\\s*REJECTION\\b",
        "bands": [[0.22, 0.32]],
    },
    {
        "rule": "SSA IL",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNINSURED\\s+MOTORISTS\\b",
        "bands": [[0.22, 0.32]],
    },
    {
        "rule": "SSA IL",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNDERINSURED\\s+MOTORISTS\\b",
        "bands": [[0.22, 0.32]],
    },

    # SSA IN
    {
        "rule": "SSA IN",
        "target": "start.any_cues",
        "pattern": "(?s)\\bINDIANA\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.022, 0.165]],
    },
    {
        "rule": "SSA IN",
        "target": "start.any_cues",
        "pattern": "(?s)\\bINDIANA.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.022, 0.165]],
    },
    {
        "rule": "SSA IN",
        "target": "helpful_cues",
        "pattern": "(?s)\\bINDIANA\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.225, 0.285]],
    },
    {
        "rule": "SSA IN",
        "target": "helpful_cues",
        "pattern": "(?s)\\bINDIANA\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.225, 0.285]],
    },
    {
        "rule": "SSA IN",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s+SELECTION\\b",
        "bands": [[0.225, 0.285]],
    },

    # SSA KS
    {
        "rule": "SSA KS",
        "target": "start.any_cues",
        "pattern": "(?s)\\bKANSAS\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.225]],
    },
    {
        "rule": "SSA KS",
        "target": "start.any_cues",
        "pattern": "(?s)\\bKANSAS.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.225]],
    },
    {
        "rule": "SSA KS",
        "target": "helpful_cues",
        "pattern": "(?s)\\bKANSAS\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.192, 0.255]],
    },
    {
        "rule": "SSA KS",
        "target": "helpful_cues",
        "pattern": "(?s)\\bKANSAS\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.192, 0.255]],
    },
    {
        "rule": "SSA KS",
        "target": "helpful_cues",
        "pattern": "(?s)\\bKANSAS.*?SPECIFIC.*?COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.192, 0.255]],
    },
    {
        "rule": "SSA KS",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s*.*?SELECTION\\b",
        "bands": [[0.192, 0.255]],
    },

    # SSA MI (range)
    {
        "rule": "SSA MI",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMICHIGAN.*?AUTOMOTIVE\\s+PROGRAM\\s+SPECIALISTS.*?WWW\\s+DMI\\s+INSURANCE\\s+COM.*",
        "bands": [[0.025, 0.115]],
    },
    {
        "rule": "SSA MI",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMICHIGAN\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.025, 0.115]],
    },
    {
        "rule": "SSA MI",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMICHIGAN.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.025, 0.115]],
    },
    {
        "rule": "SSA MI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bMICHIGAN\\s+SPECIFIC\\s+COVERAGES.*?LIMITS.*?SELECTION\\b",
        "bands": [[0.18, 0.245]],
    },
    {
        "rule": "SSA MI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bMICHIGAN\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.18, 0.245]],
    },
    {
        "rule": "SSA MI",
        "target": "end.first_cue",
        "pattern": "(?s)\\bMICHIGAN\\s+CHOICE\\s+OF\\s+BODILY\\s+INJURY\\s+LIABILITY\\s+COVERAGE\\s+LIMITS\\b",
        "bands": [[0.04, 0.088]],
    },
    {
        "rule": "SSA MI",
        "target": "end.first_cue",
        "pattern": "(?s)\\bMICHIGAN.*?CHOICE.*?BODILY.*?INJURY.*?LIABILITY.*?COVERAGE.*?LIMITS\\b",
        "bands": [[0.04, 0.088]],
    },
    {
        "rule": "SSA MI",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBY\\s+SIGNING\\s+THIS\\s+FORM.*?I\\s+ACKNOWLEDGE\\s+THAT.*?I\\s+HAVE\\s+READ\\s+THIS\\s+FORM\\s+O\\b",
        "bands": [[0.855, 0.945]],
    },
    {
        "rule": "SSA MI",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBY\\s+SIGNING\\s+THIS\\s+FORM.*?I\\s+ACKNOWLEDGE\\s+THAT\\b",
        "bands": [[0.855, 0.945]],
    },
    {
        "rule": "SSA MI",
        "target": "end.first_cue",
        "pattern": "(?s)\\bI\\s+HAVE\\s+READ\\s+THIS\\s+FORM\\s+OR\\s+HAD\\s+IT\\s+READ\\s+TO\\s+ME\\b",
        "bands": [[0.855, 0.945]],
    },

    # SSA MN
    {
        "rule": "SSA MN",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMINNESOTA\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.16]],
    },
    {
        "rule": "SSA MN",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMINNESOTA.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.16]],
    },
    {
        "rule": "SSA MN",
        "target": "helpful_cues",
        "pattern": "(?s)\\bMINNESOTA\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.21, 0.3]],
    },

    # SSA MO
    {
        "rule": "SSA MO",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMISSOURI\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.16]],
    },
    {
        "rule": "SSA MO",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMISSOURI.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.16]],
    },
    {
        "rule": "SSA MO",
        "target": "helpful_cues",
        "pattern": "(?s)\\bMISSOURI\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.21, 0.3]],
    },

    # SSA MS (range)
    {
        "rule": "SSA MS",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMISSISSIPPI\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.025, 0.15]],
    },
    {
        "rule": "SSA MS",
        "target": "start.any_cues",
        "pattern": "(?s)\\bMISSISSIPPI.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.025, 0.15]],
    },
    {
        "rule": "SSA MS",
        "target": "helpful_cues",
        "pattern": "(?s)\\bMISSISSIPPI\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.24, 0.295]],
    },
    {
        "rule": "SSA MS",
        "target": "end.first_cue",
        "pattern": "(?s)\\bPRODUCER[’'`]?S\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.984, 1.031]],
    },
    {
        "rule": "SSA MS",
        "target": "end.first_cue",
        "pattern": "(?s)\\bPRODUCER\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.984, 1.031]],
    },
    {
        "rule": "SSA MS",
        "target": "end.first_cue",
        "pattern": "(?s)\\bPRODUCERS\\s+SIGNATURE\\s+OF\\s+COMPLETION\\b",
        "bands": [[0.984, 1.031]],
    },
    {
        "rule": "SSA MS",
        "target": "end.first_cue",
        "pattern": "(?s)\\bPRODUCER.*?SIGNATURE.*?COMPLETION\\b",
        "bands": [[0.984, 1.031]],
    },

    # SSA NM (range)
    {
        "rule": "SSA NM",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNEW\\s+MEXICO\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.035, 0.15]],
    },
    {
        "rule": "SSA NM",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNEW\\s+MEXICO.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.035, 0.15]],
    },
    {
        "rule": "SSA NM",
        "target": "helpful_cues",
        "pattern": "(?s)\\bNEW\\s+MEXICO\\s+LAW\\s+PERMITS\\s+YOU\\s+TO\\s+MAKE\\s+CERTAIN\\s+DECISIONS\\s+REGARDING\\s+UNIN\\b",
        "bands": [[0.12, 0.17]],
    },
    {
        "rule": "SSA NM",
        "target": "helpful_cues",
        "pattern": "(?s)\\bNEW\\s+MEXICO\\s+LAW\\s+PERMITS\\b",
        "bands": [[0.12, 0.17]],
    },
    {
        "rule": "SSA NM",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNINSURED\\s+MOTORISTS\\s+COVERAGE\\b",
        "bands": [[0.12, 0.17]],
    },
    {
        "rule": "SSA NM",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT[’'`]?S\\s+SIGNATURE\\b",
        "bands": [[0.607, 0.661]],
    },
    {
        "rule": "SSA NM",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT\\s+SIGNATURE\\b",
        "bands": [[0.607, 0.661]],
    },
    {
        "rule": "SSA NM",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANTS\\s+SIGNATURE\\b",
        "bands": [[0.607, 0.661]],
    },

    # SSA NC
    {
        "rule": "SSA NC",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNORTH\\s+CAROLINA\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.03, 0.118]],
    },
    {
        "rule": "SSA NC",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNORTH\\s+CAROLINA.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.03, 0.118]],
    },
    {
        "rule": "SSA NC",
        "target": "helpful_cues",
        "pattern": "(?s)\\bOPTIONAL\\s+SELECTION\\s+OF\\s+UNINSURED.*?UNDERINSURED\\s+MOTORISTS\\s+COVERAGE\\s+L\\b",
        "bands": [[0.277, 0.305]],
    },
    {
        "rule": "SSA NC",
        "target": "helpful_cues",
        "pattern": "(?s)\\bOPTIONAL\\s+SELECTION\\s+OF\\s+UNINSURED\\s+MOTORISTS\\s+COVERAGE\\b",
        "bands": [[0.277, 0.305]],
    },
    {
        "rule": "SSA NC",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNDERINSURED\\s+MOTORISTS\\s+COVERAGE\\s+LIMITS\\b",
        "bands": [[0.277, 0.305]],
    },
    {
        "rule": "SSA NC",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNINSURED.*?UNDERINSURED\\s+MOTORISTS\\b",
        "bands": [[0.277, 0.305]],
    },

    # SSA NV
    {
        "rule": "SSA NV",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNEVADA\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.128]],
    },
    {
        "rule": "SSA NV",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNEVADA.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.128]],
    },
    {
        "rule": "SSA NV",
        "target": "helpful_cues",
        "pattern": "(?s)\\bNEVADA\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.2, 0.251]],
    },

    # SSA NY
    {
        "rule": "SSA NY",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNEW\\s+YORK\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.03, 0.146]],
    },
    {
        "rule": "SSA NY",
        "target": "start.any_cues",
        "pattern": "(?s)\\bNEW\\s+YORK.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.03, 0.146]],
    },
    {
        "rule": "SSA NY",
        "target": "helpful_cues",
        "pattern": "(?s)\\bNEW\\s+YORK\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.236, 0.275]],
    },

    # SSA OH
    {
        "rule": "SSA OH",
        "target": "start.any_cues",
        "pattern": "(?s)\\bOHIO\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.033, 0.112]],
    },
    {
        "rule": "SSA OH",
        "target": "start.any_cues",
        "pattern": "(?s)\\bOHIO.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.033, 0.112]],
    },
    {
        "rule": "SSA OH",
        "target": "helpful_cues",
        "pattern": "(?s)\\bOHIO\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.158, 0.195]],
    },

    # SSA OK
    {
        "rule": "SSA OK",
        "target": "start.any_cues",
        "pattern": "(?s)\\bOKLAHOMA\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.105]],
    },
    {
        "rule": "SSA OK",
        "target": "start.any_cues",
        "pattern": "(?s)\\bOKLAHOMA.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.0, 0.105]],
    },
    {
        "rule": "SSA OK",
        "target": "helpful_cues",
        "pattern": "(?s)\\bOKLAHOMA\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.21, 0.233]],
    },

    # SSA OR
    {
        "rule": "SSA OR",
        "target": "start.any_cues",
        "pattern": "(?s)\\bOREGON\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.04, 0.16]],
    },
    {
        "rule": "SSA OR",
        "target": "start.any_cues",
        "pattern": "(?s)\\bOREGON.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.04, 0.16]],
    },
    {
        "rule": "SSA OR",
        "target": "helpful_cues",
        "pattern": "(?s)\\bOREGON\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.252, 0.308]],
    },

    # SSA PA (range)
    {
        "rule": "SSA PA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bPENNSYLVANIA\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.04, 0.107]],
    },
    {
        "rule": "SSA PA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bPENNSYLVANIA.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.04, 0.107]],
    },
    {
        "rule": "SSA PA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bPENNSYLVANIA\\s+LAW\\s+PERMITS\\s+YOU\\s+TO\\s+MAKE\\s+CERTAIN\\s+DECISIONS\\s+REGARDING\\s+UN\\b",
        "bands": [[0.185, 0.238]],
    },
    {
        "rule": "SSA PA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bPENNSYLVANIA\\s+LAW\\s+PERMITS\\b",
        "bands": [[0.185, 0.238]],
    },
    {
        "rule": "SSA PA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNINSURED.*?UNDERINSURED\\s+MOTORISTS\\s+COVERAGE\\b",
        "bands": [[0.325, 0.357]],
    },
    {
        "rule": "SSA PA",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT[’'`]?S\\s+SIGNATURE\\b",
        "bands": [[0.964, 1.05]],
    },
    {
        "rule": "SSA PA",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT\\s+SIGNATURE\\b",
        "bands": [[0.964, 1.05]],
    },
    {
        "rule": "SSA PA",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANTS\\s+SIGNATURE\\b",
        "bands": [[0.964, 1.05]],
    },
    {
        "rule": "SSA PA",
        "target": "end.first_cue",
        "pattern": "(?s)\\bFIRST\\s+PARTY\\s+BENEFITS\\s+NOTICE\\b",
        "bands": [[0.421, 0.464]],
    },

    # SSA SC (range)
    {
        "rule": "SSA SC",
        "target": "start.any_cues",
        "pattern": "(?s)\\bSOUTH\\s+CAROLINA\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.035, 0.111]],
    },
    {
        "rule": "SSA SC",
        "target": "start.any_cues",
        "pattern": "(?s)\\bSOUTH\\s+CAROLINA.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.035, 0.111]],
    },
    {
        "rule": "SSA SC",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT[’'`]?S\\s+SIGNATURE\\b",
        "bands": [[0.955, 0.995]],
    },
    {
        "rule": "SSA SC",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT\\s+SIGNATURE\\b",
        "bands": [[0.955, 0.995]],
    },
    {
        "rule": "SSA SC",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANTS\\s+SIGNATURE\\b",
        "bands": [[0.955, 0.995]],
    },

    # SSA RI
    {
        "rule": "SSA RI",
        "target": "start.any_cues",
        "pattern": "(?s)\\bRHODE\\s+ISLAND\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.039, 0.112]],
    },
    {
        "rule": "SSA RI",
        "target": "start.any_cues",
        "pattern": "(?s)\\bRHODE\\s+ISLAND.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.039, 0.112]],
    },
    {
        "rule": "SSA RI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bRHODE\\s+ISLAND\\s+LAW\\s+PERMITS\\s+YOU\\s+TO\\s+MAKE\\s+CERTAIN\\s+DECISIONS\\s+REGARDING\\s+UN\\b",
        "bands": [[0.195, 0.245]],
    },
    {
        "rule": "SSA RI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bRHODE\\s+ISLAND\\s+LAW\\s+PERMITS\\b",
        "bands": [[0.195, 0.245]],
    },
    {
        "rule": "SSA RI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNINSURED\\s+MOTORISTS\\s+COVERAGE\\b",
        "bands": [[0.195, 0.245]],
    },

    # SSA TN
    {
        "rule": "SSA TN",
        "target": "start.any_cues",
        "pattern": "(?s)\\bTENNESSEE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.02, 0.11]],
    },
    {
        "rule": "SSA TN",
        "target": "start.any_cues",
        "pattern": "(?s)\\bTENNESSEE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.02, 0.11]],
    },
    {
        "rule": "SSA TN",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTENNESSEE\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.185, 0.233]],
    },

    # SSA TX
    {
        "rule": "SSA TX",
        "target": "start.any_cues",
        "pattern": "(?s)\\bTEXAS\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.022, 0.135]],
    },
    {
        "rule": "SSA TX",
        "target": "start.any_cues",
        "pattern": "(?s)\\bTEXAS.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.022, 0.135]],
    },
    {
        "rule": "SSA TX",
        "target": "helpful_cues",
        "pattern": "(?s)\\bTEXAS\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.22, 0.262]],
    },

    # SSA UT
    {
        "rule": "SSA UT",
        "target": "start.any_cues",
        "pattern": "(?s)\\bUTAH\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.043, 0.106]],
    },
    {
        "rule": "SSA UT",
        "target": "start.any_cues",
        "pattern": "(?s)\\bUTAH.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.043, 0.106]],
    },
    {
        "rule": "SSA UT",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUTAH\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.159, 0.196]],
    },

    # SSA VA
    {
        "rule": "SSA VA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bVIRGINIA\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.041, 0.112]],
    },
    {
        "rule": "SSA VA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bVIRGINIA.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.041, 0.112]],
    },
    {
        "rule": "SSA VA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bVIRGINIA\\s+LAW\\s+PERMITS\\s+YOU\\s+TO\\s+MAKE\\s+CERTAIN\\s+DECISIONS\\s+REGARDING\\s+UNINSU\\b",
        "bands": [[0.125, 0.165]],
    },
    {
        "rule": "SSA VA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bVIRGINIA\\s+LAW\\s+PERMITS\\b",
        "bands": [[0.125, 0.165]],
    },
    {
        "rule": "SSA VA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNINSURED\\s+MOTORISTS\\s+COVERAGE\\b",
        "bands": [[0.291, 0.33]],
    },

    # SSA WA
    {
        "rule": "SSA WA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bWASHINGTON\\s+GARAGE\\s+INSURANCE\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.024, 0.122]],
    },
    {
        "rule": "SSA WA",
        "target": "start.any_cues",
        "pattern": "(?s)\\bWASHINGTON.*?GARAGE\\s+INSURANCE.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.024, 0.122]],
    },
    {
        "rule": "SSA WA",
        "target": "helpful_cues",
        "pattern": "(?s)\\bWASHINGTON\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.207, 0.25]],
    },

    # SSA WI
    {
        "rule": "SSA WI",
        "target": "start.any_cues",
        "pattern": "(?s)\\bWISCONSIN\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.052, 0.171]],
    },
    {
        "rule": "SSA WI",
        "target": "start.any_cues",
        "pattern": "(?s)\\bWISCONSIN.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.052, 0.171]],
    },
    {
        "rule": "SSA WI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bWISCONSIN\\s+SPECIFIC\\s+COVERAGES\\b",
        "bands": [[0.252, 0.32]],
    },
    {
        "rule": "SSA WI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bLIMITS\\s+SELECTION\\b",
        "bands": [[0.252, 0.32]],
    },
    {
        "rule": "SSA WI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNINSURED\\s+MOTORISTS\\b",
        "bands": [[0.357, 0.422]],
    },
    {
        "rule": "SSA WI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bUNDERINSURED\\s+MOTORISTS\\b",
        "bands": [[0.357, 0.422]],
    },
    {
        "rule": "SSA WI",
        "target": "helpful_cues",
        "pattern": "(?s)\\bCOVERAGE\\b",
        "bands": [[0.357, 0.422]],
    },

    # SSA CT (range)
    {
        "rule": "SSA CT",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCONNECTICUT.*?AUTOMOTIVE\\s+PROGRAM\\s+SPECIALISTS.*?WWW\\s+DMI\\s+INSURANCE\\s+CO\\b",
        "bands": [[0.046, 0.107]],
    },
    {
        "rule": "SSA CT",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCONNECTICUT\\s+STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.046, 0.107]],
    },
    {
        "rule": "SSA CT",
        "target": "start.any_cues",
        "pattern": "(?s)\\bCONNECTICUT.*?STATE\\s+SPECIFIC\\s+APPLICATION\\b",
        "bands": [[0.046, 0.107]],
    },
    {
        "rule": "SSA CT",
        "target": "helpful_cues",
        "pattern": "(?s)\\bAUTOMOTIVE\\s+PROGRAM\\s+SPECIALISTS\\b",
        "bands": [[0.046, 0.107]],
    },
    {
        "rule": "SSA CT",
        "target": "helpful_cues",
        "pattern": "(?s)\\bWWW\\s+DMI\\s+INSURANCE\\s+COM\\b",
        "bands": [[0.046, 0.107]],
    },
    {
        "rule": "SSA CT",
        "target": "helpful_cues",
        "pattern": "(?s)\\bDMI\\s+INSURANCE\\b",
        "bands": [[0.046, 0.107]],
    },
    {
        "rule": "SSA CT",
        "target": "end.first_cue",
        "pattern": "(?s)\\bAPPLICANT[’'`]?S\\s+SIGNATURE\\b",
        "bands": [[0.965, 1.09]],
    },
    {
        "rule": "SSA CT",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER[’'`]?S\\s+SIGNATURE\\b",
        "bands": [[1.09, 1.48]],
    },
    {
        "rule": "SSA CT",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKER\\s+SIGNATURE\\b",
        "bands": [[1.09, 1.48]],
    },
    {
        "rule": "SSA CT",
        "target": "end.first_cue",
        "pattern": "(?s)\\bBROKERS\\s+SIGNATURE\\b",
        "bands": [[1.09, 1.48]],
    },
]

