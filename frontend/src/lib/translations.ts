export type Lang = "EN" | "AS" | "MN";

const translations: Record<Lang, Record<string, string>> = {
  EN: {
    // Nav
    "nav.commandCenter": "Command Center",
    "nav.reports": "Reports",
    "nav.alerts": "Alerts",
    "nav.roads": "Roads",
    "nav.weather": "Weather",
    "nav.emergency": "Emergency",
    "nav.insights": "Insights",
    "nav.about": "About",
    "nav.home": "Home",
    "nav.sensors": "Sensors",
    "nav.satellite": "Satellite",
    "nav.health": "Health",
    "nav.data": "Data",

    // TopBar header
    "header.govt": "Government of India",
    "header.division": "Geo-Sciences Division",
    "header.subtitle": "Landslide Early Warning System · North Eastern Region",
    "header.systemOnline": "SYSTEM ONLINE",

    // Sidebar tabs
    "tab.overview": "Overview",
    "tab.intelligence": "Intelligence",
    "tab.scenario": "Scenario",
    "tab.operations": "Operations",
    "tab.forecast": "Forecast",

    // Sidebar - Data Status
    "data.status": "DATA STATUS",

    // Sidebar - AreaRiskPanel
    "risk.currentRisk": "CURRENT RISK",
    "risk.responsePriority": "RESPONSE PRIORITY",
    "risk.possibleImpact": "POSSIBLE IMPACT",
    "risk.rainfall": "RAINFALL",
    "risk.soilMoisture": "SOIL MOISTURE",
    "risk.lastUpdated": "Last updated",

    // Severity labels
    "sev.low": "Low",
    "sev.moderate": "Moderate",
    "sev.high": "High",
    "sev.critical": "Critical",

    // Response priority
    "priority.immediate": "IMMEDIATE",
    "priority.highPriority": "HIGH PRIORITY",
    "priority.watch": "WATCH",
    "priority.routine": "ROUTINE",

    // Slope states
    "slope.stable": "Stable",
    "slope.stressed": "Stressed",
    "slope.degrading": "Degrading",
    "slope.critical": "Critical",

    // Buttons
    "btn.reportLandslide": "📷 + Report a Landslide",

    // Alert banner
    "alert.title": "⚠ ALERT",
    "alert.message": "Slope instability detected. Conditions are outside safe levels.",
    "alert.deteriorating": "deteriorating",

    // Map legend
    "legend.landslideRisk": "Landslide Risk",
    "legend.landslideHotspot": "Landslide Hotspot",
    "legend.riskZone": "Risk Zone",
    "legend.riskIntensity": "Risk Intensity",
    "legend.advisory": "Zone-level advisory",

    // CriticalSlopeCard
    "slope.instabilityDetected": "SLOPE INSTABILITY DETECTED",
    "slope.assessment": "SLOPE ASSESSMENT",
    "slope.susceptibility": "Susceptibility",
    "slope.recentRisk": "Recent Risk",
    "slope.rainfall72h": "72h Rainfall",
    "slope.soilMoisture": "Soil Moisture",
    "slope.stressIndex": "Slope Stress Index",
    "slope.keyFactors": "Key Factors",
    "slope.summary": "Summary:",
    "slope.recommendedAction": "Recommended Action",
    "slope.honesty": "Assessment based on model outputs, not confirmed field observation.",

    // Tooltip texts
    "tooltip.susceptibility": "Static terrain-based risk from slope angle, elevation, geology, and land cover. Does not change with weather.",
    "tooltip.recentRisk": "Dynamic event-driven risk from recent rainfall and soil moisture. Satellite SAR is excluded from risk.",
    "tooltip.soilMoisture": "Soil-water proxy (modeled; SMAP observed only with live provider). Above 45% indicates saturated conditions that increase landslide risk.",

    // Action labels
    "action.escalate": "Escalate",
    "action.issueAdvisory": "Issue advisory",
    "action.verifyLocally": "Verify locally",
    "action.monitor": "Monitor",

    // Reports page
    "reports.title": "CITIZEN REPORTS",
    "reports.subtitle": "Community-submitted landslide observations pending validation",
    "reports.noReports": "No reports submitted yet",
    "reports.emptyHint": "Reports from citizens will appear here",

    // Alerts page
    "alerts.title": "EARLY WARNING ALERTS",
    "alerts.subtitle": "Dispatched advisories and alert history for all monitored zones",
    "alerts.noAlerts": "No alerts dispatched yet",
    "alerts.emptyHint": "Alerts will appear here when advisories are sent to zones",
    "alerts.viewOnMap": "View on map",

    // Soil moisture labels
    "soil.normal": "Normal",
    "soil.moist": "Moist",
    "soil.saturated": "Saturated",

    // Common
    "common.loading": "Loading…",
    "common.selectZone": "Select a zone on the map",
    "common.clickPolygon": "Click any polygon to view detailed risk assessment",
  },

  AS: {
    // Nav
    "nav.commandCenter": "কমান্ড চেংটাৰ",
    "nav.reports": "প্ৰতিবেদন",
    "nav.alerts": "সতৰ্কবাৰ্তা",
    "nav.roads": "ৰাস্তা",
    "nav.weather": "আবহাওয়া",
    "nav.emergency": "জৰুৰীকালীন",
    "nav.insights": "অন্তৰ্দৃষ্টি",
    "nav.about": "বিষয়ে",
    "nav.home": "হোম",
    "nav.sensors": "সেংচৰ",
    "nav.satellite": "উপগ্ৰহ",
    "nav.health": "স্বাস্থ্য",
    "nav.data": "ডেটা",

    // TopBar header
    "header.govt": "ভাৰত চৰকাৰ",
    "header.division": "জিও-বিজ্ঞান বিভাগ",
    "header.subtitle": "ভূমিধস প্ৰাথমিক সতৰ্কীকৰণ ব্যৱস্থা · উত্তৰ-পূৰ্ব ঞ্চল",
    "header.systemOnline": "চিস্টেম অনলাইন",

    // Sidebar tabs
    "tab.overview": "সাংক্ষিপ্ত বিবৰণ",
    "tab.intelligence": "তথ্য",
    "tab.scenario": "পৰিস্থিতি",
    "tab.operations": "কাৰ্যসূচী",
    "tab.forecast": "পূৰ্বাভাস",

    // Sidebar - Data Status
    "data.status": "ডেটা অৱস্থা",

    // Sidebar - AreaRiskPanel
    "risk.currentRisk": "বৰ্তমান বিপদ",
    "risk.responsePriority": "প্ৰতিক্ৰিয়া অগ্ৰাধিকাৰ",
    "risk.possibleImpact": "সম্ভাব্য প্ৰভাৱ",
    "risk.rainfall": "বৃষ্টিপাত",
    "risk.soilMoisture": "মাটিৰ আৰ্দ্ৰতা",
    "risk.lastUpdated": "শেহতিয়াকৈ আপডেট",

    // Severity labels
    "sev.low": "নিম্ন",
    "sev.moderate": "মধ্যম",
    "sev.high": "উচ্চ",
    "sev.critical": "গুৰুতৰ",

    // Response priority
    "priority.immediate": "তৎক্ষণাৎ",
    "priority.highPriority": "উচ্চ অগ্ৰাধিকাৰ",
    "priority.watch": "সতৰ্ক",
    "priority.routine": "সাধাৰণ",

    // Slope states
    "slope.stable": "স্থিৰ",
    "slope.stressed": "চাপগ্ৰস্ত",
    "slope.degrading": "অবনতিশীল",
    "slope.critical": "গুৰুতৰ",

    // Buttons
    "btn.reportLandslide": "📷 + ভূমিধস জনাওক",

    // Alert banner
    "alert.title": "⚠ সতৰ্ক",
    "alert.message": "ভূমিৰ অস্থিৰতা চিহ্নিত হৈছে। অৱস্থা নিৰাপদ স্তৰৰ বাহিৰত।",
    "alert.deteriorating": "বিগৰা হৈ আছে",

    // Map legend
    "legend.landslideRisk": "ভূমিধস বিপদ",
    "legend.landslideHotspot": "ভূমিধস হটস্পট",
    "legend.riskZone": "বিপদ অঞ্চল",
    "legend.riskIntensity": "বিপদৰ তীব্ৰতা",
    "legend.advisory": "অঞ্চল-স্তৰৰ পৰামৰ্শ",

    // CriticalSlopeCard
    "slope.instabilityDetected": "ভূমিৰ অস্থিৰতা চিহ্নিত",
    "slope.assessment": "ভূমি মূল্যায়ন",
    "slope.susceptibility": "সংবেদনশীলতা",
    "slope.recentRisk": "শেহতিয়াৰ বিপদ",
    "slope.rainfall72h": "৭২ ঘণ্টা বৃষ্টিপাত",
    "slope.soilMoisture": "মাটিৰ আৰ্দ্ৰতা",
    "slope.stressIndex": "ভূমি চাপ সূচক",
    "slope.keyFactors": "মূল কাৰণ",
    "slope.summary": "সাৰাংশ:",
    "slope.recommendedAction": "পৰামৰ্শিত কাৰ্য",
    "slope.honesty": "মডেল আউটপুটৰ ওপৰত ভিত্তি কৰি মূল্যায়ন, পুষ্টি ক্ষেত্র পৰ্যবেক্ষণ নহয়।",

    // Tooltip texts
    "tooltip.susceptibility": "ভূমিৰ কোণ, উচ্চতা, ভূ-বিজ্ঞান আৰু ভূমি আৱৰণৰ পৰা স্থিৰ ভূমি-ভিত্তিক বিপদ। বতুৰৰ সৈতে সলনি নহয়।",
    "tooltip.recentRisk": "শেহতিয়াৰ বৃষ্টিপাত, মাটিৰ আৰ্দ্ৰতা আৰু উপগ্ৰহ-চিহ্নিত ভূমি সঞ্চলনৰ পৰা গতিশীল ঘটনা-চালিত বিপদ।",
    "tooltip.soilMoisture": "মাটিৰ পানীৰ প্ৰক্সি (মডেল-ভিত্তিক; লাইভ প্ৰদানকাৰী থাকিলেহে SMAP পৰ্যবেক্ষিত)। ৪৫%ৰ ওপৰত ভূমিধসৰ বিপদ বঢ়ায়।",

    // Action labels
    "action.escalate": "উন্নীত কৰক",
    "action.issueAdvisory": "পৰামৰ্শ জাৰি কৰক",
    "action.verifyLocally": "স্থানীয়ভাৱে যাচাই কৰক",
    "action.monitor": "পৰ্যবেক্ষণ কৰক",

    // Reports page
    "reports.title": "নাগৰিক প্ৰতিবেদন",
    "reports.subtitle": "বৈধকৰণৰ অপেক্ষাত সম্প্ৰদায়-জমা ভূমিধসৰ পৰ্যবেক্ষণ",
    "reports.noReports": "এতিয়া কোনো প্ৰতিবেদন দাখিল হোৱা নাই",
    "reports.emptyHint": "নাগৰিকৰ পৰা প্ৰতিবেদন ইয়াত প্ৰদৰ্শন হ'ব",

    // Alerts page
    "alerts.title": "প্ৰাথমিক সতৰ্কীকৰণ সতৰ্কবাৰ্তা",
    "alerts.subtitle": "সকলো পৰ্যবেক্ষিত অঞ্চলৰ বাবে পঠোৱা পৰামৰ্শ আৰু সতৰ্ক ইতিহাস",
    "alerts.noAlerts": "এতিয়া কোনো সতৰ্কবাৰ্তা পঠোৱা হোৱা নাই",
    "alerts.emptyHint": "পৰামৰ্শ পঠোৱাৰ পিছত সতৰ্কবাৰ্তা ইয়াত প্ৰদৰ্শন হ'ব",
    "alerts.viewOnMap": "মানচিত্ৰত চাওক",

    // Soil moisture labels
    "soil.normal": "স্বাভাৱিক",
    "soil.moist": "আৰ্দ্ৰ",
    "soil.saturated": "পৰিপূৰ্ণ",

    // Common
    "common.loading": "ল'ড হৈ আছে…",
    "common.selectZone": "মানচিত্ৰত এটা অঞ্চল বাছনি কৰক",
    "common.clickPolygon": "বিস্তাৰিত বিপদ মূল্যায়ন চাওক বাবে যিকোনো বহুভুজ ক্লিক কৰক",
  },

  MN: {
    // Nav
    "nav.commandCenter": "কমান্ড সেংতাৰ",
    "nav.reports": "পুৰকথন",
    "nav.alerts": "সতৰ্ক",
    "nav.roads": "ৰাস্তা",
    "nav.weather": "আবহাওয়া",
    "nav.emergency": "জৰুৰীকালীন",
    "nav.insights": "অন্তৰ্দৃষ্টি",
    "nav.about": "বিষয়ে",
    "nav.home": "হোম",
    "nav.sensors": "সেংচৰ",
    "nav.satellite": "উপগ্ৰহ",
    "nav.health": "স্বাস্থ্য",
    "nav.data": "ডেটা",

    // TopBar header
    "header.govt": "ভাৰত সরকার",
    "header.division": "জিও-বিজ্ঞান বিভাগ",
    "header.subtitle": "লিংগাই সতৰ্কীকৰণ ব্যৱস্থা · ময়ে পৌরবা",
    "header.systemOnline": "চিস্টেম অনলাইন",

    // Sidebar tabs
    "tab.overview": "সারসংক্ষেপ",
    "tab.intelligence": "তথ্য",
    "tab.scenario": "পৰিস্থিতি",
    "tab.operations": "কাৰ্যসূচী",
    "tab.forecast": "পূৰ্বাভাস",

    // Sidebar - Data Status
    "data.status": "ডেটা অৱস্থা",

    // Sidebar - AreaRiskPanel
    "risk.currentRisk": "হন্নানগী পীরিব",
    "risk.responsePriority": "মতুং অগ্ৰাধিকাৰ",
    "risk.possibleImpact": "যান্ত্রিক পীরিব",
    "risk.rainfall": "মেং পাত্রিব",
    "risk.soilMoisture": "মাটি অমৃতা",
    "risk.lastUpdated": "অকুনা আপডেট",

    // Severity labels
    "sev.low": "য়াল",
    "sev.moderate": "ময়াম",
    "sev.high": "অচৌ",
    "sev.critical": "তীব্ৰ",

    // Response priority
    "priority.immediate": "তৎক্ষণাৎ",
    "priority.highPriority": "অচৌ অগ্ৰাধিকাৰ",
    "priority.watch": "সতৰ্ক",
    "priority.routine": "সাধাৰণ",

    // Slope states
    "slope.stable": "স্থিৰ",
    "slope.stressed": "চাপ",
    "slope.degrading": "অবনতি",
    "slope.critical": "তীব্ৰ",

    // Buttons
    "btn.reportLandslide": "📷 + লিংগাই পুৰকথন তুলক",

    // Alert banner
    "alert.title": "⚠ সতৰ্ক",
    "alert.message": "মাটি অস্থিৰতা খংজিবা লাগে। অৱস্থা নিৰাপদ খন্দ্র লাই ফাওবা লাগে।",
    "alert.deteriorating": "য়াল লৈ",

    // Map legend
    "legend.landslideRisk": "লিংগাই পীরিব",
    "legend.landslideHotspot": "লিংগাই হটস্পট",
    "legend.riskZone": "পীরিব খন্দ্র",
    "legend.riskIntensity": "পীরিব তীব্ৰতা",
    "legend.advisory": "খন্দ্র-স্তৰৰ পৰামৰ্শ",

    // CriticalSlopeCard
    "slope.instabilityDetected": "মাটি অস্থিৰতা খংজিবা লাগে",
    "slope.assessment": "মাটি মূল্যায়ন",
    "slope.susceptibility": "সংবেদনশীলতা",
    "slope.recentRisk": "হন্নানগী পীরিব",
    "slope.rainfall72h": "৭২ ঘণ্টা মেং পাত্রিব",
    "slope.soilMoisture": "মাটি অমৃতা",
    "slope.stressIndex": "মাটি চাপ সূচক",
    "slope.keyFactors": "তীব্ৰ কাৰণ",
    "slope.summary": "সাৰাংশ:",
    "slope.recommendedAction": "মতুং কাৰ্য",
    "slope.honesty": "মডেল আউটপুটৰ ওপৰত ভিত্তি কৰি মূল্যায়ন, পুষ্টি ক্ষেত্র পৰ্যবেক্ষণ নহয়।",

    // Tooltip texts
    "tooltip.susceptibility": "মাটি কোণ, উচ্চতা, ভূ-বিজ্ঞান আৰু ভূমি আৱৰণৰ পৰা স্থিৰ মাটি-ভিত্তিক পীরিব। বতুৰৰ সৈতে সলনি নহয়।",
    "tooltip.recentRisk": "হন্নানগী মেং পাত্রিব, মাটি অমৃতা আৰু উপগ্ৰহ-খংজিবা মাটি সঞ্চলনৰ পৰা গতিশীল ঘটনা-চালিত পীরিব।",
    "tooltip.soilMoisture": "মাটি পানী প্ৰক্সি (মডেল-ভিত্তিক; লাইভ প্ৰদানকাৰী লৈৰবদি SMAP খংজিনবা)। ৪৫%গী মথক্তা লিংগাই পীরিব হেনগৎলি।",

    // Action labels
    "action.escalate": "উন্নীত তুলক",
    "action.issueAdvisory": "পৰামৰ্শ তুলক",
    "action.verifyLocally": "স্থানীয়ভাৱে যাচাই তুলক",
    "action.monitor": "পৰ্যবেক্ষণ তুলক",

    // Reports page
    "reports.title": "নাগৰিক পুৰকথন",
    "reports.subtitle": "বৈধকৰণৰ অপেক্ষাত সম্প্ৰদায়-জমা লিংগাইৰ পৰ্যবেক্ষণ",
    "reports.noReports": "দিহান কোনো পুৰকথন তুলা হোৱা নাই",
    "reports.emptyHint": "নাগৰিকৰ পৰা পুৰকথন ইয়াত প্ৰদৰ্শন হ'ব",

    // Alerts page
    "alerts.title": "প্ৰাথমিক সতৰ্কীকৰণ সতৰ্ক",
    "alerts.subtitle": "সকলো পৰ্যবেক্ষিত খন্দ্রৰ বাবে পঠোৱা পৰামৰ্শ আৰু সতৰ্ক ইতিহাস",
    "alerts.noAlerts": "দিহান কোনো সতৰ্ক পঠোৱা হোৱা নাই",
    "alerts.emptyHint": "পৰামৰ্শ পঠোৱাৰ পিছত সতৰ্ক ইয়াত প্ৰদৰ্শন হ'ব",
    "alerts.viewOnMap": "মানচিত্ৰত চাওক",

    // Soil moisture labels
    "soil.normal": "স্বাভাৱিক",
    "soil.moist": "অমৃতা",
    "soil.saturated": "পৰিপূৰ্ণ",

    // Common
    "common.loading": "ল'ড হৈ আছে…",
    "common.selectZone": "মানচিত্ৰত এটা খন্দ্র বাছনি তুলক",
    "common.clickPolygon": "বিস্তাৰিত পীরিব মূল্যায়ন চাওক বাবে যিকোনো বহুভুজ ক্লিক তুলক",
  },
};

export default translations;
