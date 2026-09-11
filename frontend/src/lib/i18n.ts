export type Lang = "en" | "hi" | "bn" | "kha" | "garo";

export const LANG_LABELS: Record<Lang, string> = {
  en: "English",
  hi: "हिन्दी",
  bn: "বাংলা",
  kha: "Khasi",
  garo: "Garo",
};

export const LANG_FLAGS: Record<Lang, string> = {
  en: "EN", hi: "HI", bn: "BN", kha: "KH", garo: "GA",
};

type TranslationKeys = {
  // Header
  appName: string;
  tagline: string;
  // Nav
  navCommand: string;
  navDashboard: string;
  navRoads: string;
  navWeather: string;
  navEmergency: string;
  navReports: string;
  navAlerts: string;
  navInsights: string;
  navAbout: string;
  // Sidebar
  zoneDetail: string;
  intelligence: string;
  scenario: string;
  reportLandslip: string;
  // Zone
  slopeState: string;
  riskScore: string;
  confidence: string;
  areaOverview: string;
  keyIndicators: string;
  rfStatic: string;
  mambaDynamic: string;
  rainfall24h: string;
  soilMoisture: string;
  rainfallChart: string;
  riskOverTime: string;
  riskTrajectory: string;
  slopeAnalysis: string;
  perCellIntelligence: string;
  riskDrivers: string;
  terrainSatellite: string;
  recentEvents: string;
  modelProvenance: string;
  alertDispatch: string;
  // Alerts
  alertHigh: string;
  alertVeryHigh: string;
  alertModerate: string;
  alertLow: string;
  dispatchAlert: string;
  language: string;
  // Scenario
  rainfallScenario: string;
  whatIf: string;
  runScenario: string;
  current: string;
  extreme: string;
  continuedRainfall: string;
  // Intelligence
  hotspots: string;
  governmentIntel: string;
  topHotspots: string;
  riskIntensification: string;
  // Offline
  online: string;
  offline: string;
  queued: string;
  syncing: string;
  // Common
  loading: string;
  noData: string;
  retry: string;
  escalate: string;
  issueAdvisory: string;
  monitor: string;
  // Road
  roadConnectivity: string;
  roadAccessGood: string;
  roadAccessLimited: string;
  roadAccessPoor: string;
  drainage: string;
  ruggedness: string;
  // Weather
  weatherForecast: string;
  forecastTitle: string;
  next24h: string;
  next48h: string;
  next72h: string;
  rainfallExpected: string;
  stormWarning: string;
  noStorm: string;
  // Emergency
  emergencyPriority: string;
  priorityHigh: string;
  priorityMedium: string;
  priorityLow: string;
  responseTeams: string;
  estimatedArrival: string;
  evacRoutes: string;
  shelterStatus: string;
};

const translations: Record<Lang, TranslationKeys> = {
  en: {
    appName: "GEO-SENTINEL",
    tagline: "AI Landslide Early Warning",
    navCommand: "Command Center",
    navDashboard: "Risk Dashboard",
    navRoads: "Roads",
    navWeather: "Weather",
    navEmergency: "Emergency",
    navReports: "Reports",
    navAlerts: "Alerts",
    navInsights: "Data & Insights",
    navAbout: "About",
    zoneDetail: "Zone Detail",
    intelligence: "Intelligence",
    scenario: "Scenario",
    reportLandslip: "+ REPORT LANDSLIP",
    slopeState: "Slope State",
    riskScore: "Risk Score",
    confidence: "Confidence",
    areaOverview: "Area Overview",
    keyIndicators: "Key Indicators",
    rfStatic: "RF Static",
    mambaDynamic: "Mamba Dynamic",
    rainfall24h: "24H Rainfall",
    soilMoisture: "Soil Moisture",
    rainfallChart: "Rainfall (96h)",
    riskOverTime: "Risk Over Time",
    riskTrajectory: "Risk Trajectory",
    slopeAnalysis: "Slope State Analysis",
    perCellIntelligence: "Per-Cell Terrain Intelligence",
    riskDrivers: "Risk Drivers & Terrain",
    terrainSatellite: "Terrain & Satellite",
    recentEvents: "Recent Events",
    modelProvenance: "Model Provenance",
    alertDispatch: "Alert Dispatch",
    alertHigh: "High Risk Advisory",
    alertVeryHigh: "Very High Risk Alert",
    alertModerate: "Moderate Risk Notice",
    alertLow: "Low Risk — No Alert",
    dispatchAlert: "Dispatch Advisory",
    language: "Language",
    rainfallScenario: "Rainfall Scenario",
    whatIf: "What-If Simulation",
    runScenario: "RUN SCENARIO",
    current: "Current",
    extreme: "Extreme",
    continuedRainfall: "Continued Rainfall",
    hotspots: "Hotspot Ranking",
    governmentIntel: "Government Intelligence",
    topHotspots: "Top Hotspots",
    riskIntensification: "Risk Intensification",
    online: "Online",
    offline: "Offline",
    queued: "queued",
    syncing: "Syncing...",
    loading: "Loading...",
    noData: "No data available",
    retry: "Retry",
    escalate: "Escalate",
    issueAdvisory: "Issue Advisory",
    monitor: "Monitor",
    roadConnectivity: "Road Connectivity",
    roadAccessGood: "Good — accessible by road",
    roadAccessLimited: "Limited — single access route",
    roadAccessPoor: "Poor — remote, limited access",
    drainage: "Drainage Proximity",
    ruggedness: "Terrain Ruggedness",
    weatherForecast: "Weather Forecast",
    forecastTitle: "Rainfall Forecast",
    next24h: "Next 24h",
    next48h: "Next 48h",
    next72h: "Next 72h",
    rainfallExpected: "Rainfall expected",
    stormWarning: "Heavy rainfall warning",
    noStorm: "No significant rainfall expected",
    emergencyPriority: "Emergency Response Priority",
    priorityHigh: "High Priority",
    priorityMedium: "Medium Priority",
    priorityLow: "Low Priority",
    responseTeams: "Response Teams",
    estimatedArrival: "Estimated Arrival",
    evacRoutes: "Evacuation Routes",
    shelterStatus: "Shelter Status",
  },
  hi: {
    appName: "जियो-सेंटिनल",
    tagline: "भूस्खलन प्रारंभिक चेतावनी",
    navCommand: "कमांड सेंटर",
    navDashboard: "जोखिम डैशबोर्ड",
    navRoads: "सड़कें",
    navWeather: "मौसम",
    navEmergency: "आपातकाल",
    navReports: "रिपोर्ट",
    navAlerts: "अलर्ट",
    navInsights: "डेटा और अंतर्दृष्टि",
    navAbout: "के बारे में",
    zoneDetail: "क्षेत्र विवरण",
    intelligence: "खुफिया",
    scenario: "परिदृश्य",
    reportLandslip: "+ भूस्खलन रिपोर्ट",
    slopeState: "ढलान स्थिति",
    riskScore: "जोखिम स्कोर",
    confidence: "विश्वास",
    areaOverview: "क्षेत्र अवलोकन",
    keyIndicators: "प्रमुख संकेतक",
    rfStatic: "आरएफ स्थैतिक",
    mambaDynamic: "मांबा गतिशील",
    rainfall24h: "24 घंटे वर्षा",
    soilMoisture: "मिट्टी की नमी",
    rainfallChart: "वर्षा (96h)",
    riskOverTime: "समय के साथ जोखिम",
    riskTrajectory: "जोखिम प्रक्षेपवक्र",
    slopeAnalysis: "ढलान स्थिति विश्लेषण",
    perCellIntelligence: "प्रति सेल भू-बुद्धिमत्ता",
    riskDrivers: "जोखिम चालक और भूभाग",
    terrainSatellite: "भूभाग और उपग्रह",
    recentEvents: "हाल की घटनाएं",
    modelProvenance: "मॉडल प्रमाण",
    alertDispatch: "अलर्ट प्रेषण",
    alertHigh: "उच्च जोखिम सलाह",
    alertVeryHigh: "अति उच्च जोखिम अलर्ट",
    alertModerate: "मध्यम जोखिम सूचना",
    alertLow: "निम्न जोखिम — कोई अलर्ट नहीं",
    dispatchAlert: "अलर्ट भेजें",
    language: "भाषा",
    rainfallScenario: "वर्षा परिदृश्य",
    whatIf: "क्या होगा अगर",
    runScenario: "परिदृश्य चलाएं",
    current: "वर्तमान",
    extreme: "चरम",
    continuedRainfall: "लगातार वर्षा",
    hotspots: "हॉटस्पॉट रैंकिंग",
    governmentIntel: "सरकारी खुफिया",
    topHotspots: "शीर्ष हॉटस्पॉट",
    riskIntensification: "जोखिम तीव्रता",
    online: "ऑनलाइन",
    offline: "ऑफलाइन",
    queued: "कतार में",
    syncing: "सिंक हो रहा है...",
    loading: "लोड हो रहा है...",
    noData: "डेटा उपलब्ध नहीं",
    retry: "पुनर्प्रयास",
    escalate: "बढ़ाएं",
    issueAdvisory: "सलाह जारी करें",
    monitor: "निगरानी",
    roadConnectivity: "सड़क कनेक्टिविटी",
    roadAccessGood: "अच्छा — सड़क से सुलभ",
    roadAccessLimited: "सीमित — एक ही मार्ग",
    roadAccessPoor: "खराब — दूरदराज, सीमित पहुंच",
    drainage: "जल निकासी निकटता",
    ruggedness: "भूभाग की खुरदरापन",
    weatherForecast: "मौसम पूर्वानुमान",
    forecastTitle: "वर्षा पूर्वानुमान",
    next24h: "अगले 24 घंटे",
    next48h: "अगले 48 घंटे",
    next72h: "अगले 72 घंटे",
    rainfallExpected: "वर्षा की उम्मीद",
    stormWarning: "भारी वर्षा चेतावनी",
    noStorm: "कोई महत्वपूर्ण वर्षा नहीं",
    emergencyPriority: "आपातकालीन प्रतिक्रिया प्राथमिकता",
    priorityHigh: "उच्च प्राथमिकता",
    priorityMedium: "मध्यम प्राथमिकता",
    priorityLow: "निम्न प्राथमिकता",
    responseTeams: "प्रतिक्रिया टीम",
    estimatedArrival: "अनुमानित आगमन",
    evacRoutes: "निकासी मार्ग",
    shelterStatus: "आश्रय स्थिति",
  },
  bn: {
    appName: "জিও-সেন্টিনেল",
    tagline: "ভূমিধস প্রাথমিক সতর্কতা",
    navCommand: "কমান্ড সেন্টার",
    navDashboard: "ঝুঁকি ড্যাশবোর্ড",
    navRoads: "সড়ক",
    navWeather: "আবহাওয়া",
    navEmergency: "জরুরি",
    navReports: "রিপোর্ট",
    navAlerts: "সতর্কতা",
    navInsights: "ডেটা ও অন্তর্দৃষ্টি",
    navAbout: "সম্পর্কে",
    zoneDetail: "অঞ্চল বিবরণ",
    intelligence: "তথ্য",
    scenario: "পরিস্থিতি",
    reportLandslip: "+ ভূমিধস রিপোর্ট",
    slopeState: "ভূস্কন্ধ অবস্থা",
    riskScore: "ঝুঁকি স্কোর",
    confidence: "আস্থা",
    areaOverview: "অঞ্চল পর্যালোচনা",
    keyIndicators: "মূল নির্দেশক",
    rfStatic: "আরএফ স্থিতিশীল",
    mambaDynamic: "মাম্বা গতিশীল",
    rainfall24h: "২৪ ঘণ্টা বৃষ্টি",
    soilMoisture: "মাটির আর্দ্রতা",
    rainfallChart: "বৃষ্টি (৯৬ ঘণ্টা)",
    riskOverTime: "সময়ের সাথে ঝুঁকি",
    riskTrajectory: "ঝুঁকি প্রক্ষেপণ",
    slopeAnalysis: "ভূস্কন্ধ অবস্থা বিশ্লেষণ",
    perCellIntelligence: "প্রতি কোষ ভূ-বুদ্ধিমত্তা",
    riskDrivers: "ঝুঁকি চালক ও ভূপ্রকৃতি",
    terrainSatellite: "ভূপ্রকৃতি ও উপগ্রহ",
    recentEvents: "সাম্প্রতিক ঘটনা",
    modelProvenance: "মডেল উৎস",
    alertDispatch: "সতর্কতা প্রেরণ",
    alertHigh: "উচ্চ ঝুঁকি পরামর্শ",
    alertVeryHigh: "অতি উচ্চ ঝুঁকি সতর্কতা",
    alertModerate: "মাঝারি ঝুঁকি বিজ্ঞপ্তি",
    alertLow: "নিম্ন ঝুঁকি — কোনো সতর্কতা নেই",
    dispatchAlert: "সতর্কতা প্রেরণ করুন",
    language: "ভাষা",
    rainfallScenario: "বৃষ্টির পরিস্থিতি",
    whatIf: "যদি হয়",
    runScenario: "পরিস্থিতি চালান",
    current: "বর্তমান",
    extreme: "চরম",
    continuedRainfall: "ক্রমাগত বৃষ্টি",
    hotspots: "হটস্পট র্যাঙ্কিং",
    governmentIntel: "সরকারি তথ্য",
    topHotspots: "শীর্ষ হটস্পট",
    riskIntensification: "ঝুঁকি তীব্রতা",
    online: "অনলাইন",
    offline: "অফলাইন",
    queued: "সারিবদ্ধ",
    syncing: "সিঙ্ক হচ্ছে...",
    loading: "লোড হচ্ছে...",
    noData: "তথ্য পাওয়া যায়নি",
    retry: "পুনরায় চেষ্টা",
    escalate: "বৃদ্ধি করুন",
    issueAdvisory: "পরামর্শ জারি করুন",
    monitor: "পর্যবেক্ষণ",
    roadConnectivity: "সড়ক সংযোগ",
    roadAccessGood: "ভালো — সড়কে প্রবেশযোগ্য",
    roadAccessLimited: "সীমিত — একটি মাত্র পথ",
    roadAccessPoor: "খারাপ — প্রত্যন্ত, সীমিত প্রবেশ",
    drainage: "পানি নিষ্কাশন নিকটতা",
    ruggedness: "ভূপ্রকৃতি খসখস",
    weatherForecast: "আবহাওয়ার পূর্বাভাস",
    forecastTitle: "বৃষ্টির পূর্বাভাস",
    next24h: "পরবর্তী ২৪ ঘণ্টা",
    next48h: "পরবর্তী ৪৮ ঘণ্টা",
    next72h: "পরবর্তী ৭২ ঘণ্টা",
    rainfallExpected: "বৃষ্টির প্রত্যাশা",
    stormWarning: "ভারী বৃষ্টি সতর্কতা",
    noStorm: "কোনো উল্লেখযোগ্য বৃষ্টি নেই",
    emergencyPriority: "জরুরি প্রতিক্রিয়া অগ্রাধিকার",
    priorityHigh: "উচ্চ অগ্রাধিকার",
    priorityMedium: "মাঝারি অগ্রাধিকার",
    priorityLow: "নিম্ন অগ্রাধিকার",
    responseTeams: "প্রতিক্রিয়া দল",
    estimatedArrival: "আনুমানিক আগমন",
    evacRoutes: "পলায়ন পথ",
    shelterStatus: "আশ্রয় অবস্থা",
  },
  kha: {
    appName: "GEO-SENTINEL",
    tagline: "Ka Jingsngew Bhaipara",
    navCommand: "Command Center",
    navDashboard: "Risk Dashboard",
    navRoads: "Kiba Jingsngew",
    navWeather: "Jingiaruh",
    navEmergency: "Emergency",
    navReports: "Ka Reports",
    navAlerts: "Ka Alerts",
    navInsights: "Data bad ka Insights",
    navAbout: "Para shnong",
    zoneDetail: "Ka Zone Detail",
    intelligence: "Intelligence",
    scenario: "Scenario",
    reportLandslip: "+ REPORT LANDSLIP",
    slopeState: "Ka Slope State",
    riskScore: "Ka Risk Score",
    confidence: "Confidence",
    areaOverview: "Area Overview",
    keyIndicators: "Key Indicators",
    rfStatic: "RF Static",
    mambaDynamic: "Mamba Dynamic",
    rainfall24h: "24H Rainfall",
    soilMoisture: "Soil Moisture",
    rainfallChart: "Rainfall (96h)",
    riskOverTime: "Risk Over Time",
    riskTrajectory: "Risk Trajectory",
    slopeAnalysis: "Slope State Analysis",
    perCellIntelligence: "Per-Cell Terrain Intelligence",
    riskDrivers: "Risk Drivers & Terrain",
    terrainSatellite: "Terrain & Satellite",
    recentEvents: "Recent Events",
    modelProvenance: "Model Provenance",
    alertDispatch: "Alert Dispatch",
    alertHigh: "High Risk Advisory",
    alertVeryHigh: "Very High Risk Alert",
    alertModerate: "Moderate Risk Notice",
    alertLow: "Low Risk",
    dispatchAlert: "Dispatch Advisory",
    language: "Ka Jingiashymat",
    rainfallScenario: "Rainfall Scenario",
    whatIf: "What-If",
    runScenario: "Run Scenario",
    current: "Current",
    extreme: "Extreme",
    continuedRainfall: "Continued Rainfall",
    hotspots: "Hotspot Ranking",
    governmentIntel: "Government Intel",
    topHotspots: "Top Hotspots",
    riskIntensification: "Risk Intensification",
    online: "Online",
    offline: "Offline",
    queued: "queued",
    syncing: "Syncing...",
    loading: "Loading...",
    noData: "No data",
    retry: "Retry",
    escalate: "Escalate",
    issueAdvisory: "Issue Advisory",
    monitor: "Monitor",
    roadConnectivity: "Road Connectivity",
    roadAccessGood: "Good — accessible by road",
    roadAccessLimited: "Limited — single route",
    roadAccessPoor: "Poor — remote, limited",
    drainage: "Drainage Proximity",
    ruggedness: "Terrain Ruggedness",
    weatherForecast: "Weather Forecast",
    forecastTitle: "Rainfall Forecast",
    next24h: "Next 24h",
    next48h: "Next 48h",
    next72h: "Next 72h",
    rainfallExpected: "Rainfall expected",
    stormWarning: "Heavy rainfall warning",
    noStorm: "No significant rainfall",
    emergencyPriority: "Emergency Response Priority",
    priorityHigh: "High Priority",
    priorityMedium: "Medium Priority",
    priorityLow: "Low Priority",
    responseTeams: "Response Teams",
    estimatedArrival: "Est. Arrival",
    evacRoutes: "Evacuation Routes",
    shelterStatus: "Shelter Status",
  },
  garo: {
    appName: "GEO-SENTINEL",
    tagline: "Kanika A'balik Agrik Ondak",
    navCommand: "Command Center",
    navDashboard: "Risk Dashboard",
    navRoads: "Kanika Dong",
    navWeather: "Jong naka",
    navEmergency: "Emergency",
    navReports: "Reports",
    navAlerts: "Alerts",
    navInsights: "Data & Insights",
    navAbout: "Fida",
    zoneDetail: "Zone Detail",
    intelligence: "Intelligence",
    scenario: "Scenario",
    reportLandslip: "+ REPORT LANDSLIP",
    slopeState: "Slope State",
    riskScore: "Risk Score",
    confidence: "Confidence",
    areaOverview: "Area Overview",
    keyIndicators: "Key Indicators",
    rfStatic: "RF Static",
    mambaDynamic: "Mamba Dynamic",
    rainfall24h: "24H Rainfall",
    soilMoisture: "Soil Moisture",
    rainfallChart: "Rainfall (96h)",
    riskOverTime: "Risk Over Time",
    riskTrajectory: "Risk Trajectory",
    slopeAnalysis: "Slope State Analysis",
    perCellIntelligence: "Per-Cell Terrain Intelligence",
    riskDrivers: "Risk Drivers & Terrain",
    terrainSatellite: "Terrain & Satellite",
    recentEvents: "Recent Events",
    modelProvenance: "Model Provenance",
    alertDispatch: "Alert Dispatch",
    alertHigh: "High Risk Advisory",
    alertVeryHigh: "Very High Risk Alert",
    alertModerate: "Moderate Risk Notice",
    alertLow: "Low Risk",
    dispatchAlert: "Dispatch Advisory",
    language: "Ma Bandubi",
    rainfallScenario: "Rainfall Scenario",
    whatIf: "What-If",
    runScenario: "Run Scenario",
    current: "Current",
    extreme: "Extreme",
    continuedRainfall: "Continued Rainfall",
    hotspots: "Hotspot Ranking",
    governmentIntel: "Government Intel",
    topHotspots: "Top Hotspots",
    riskIntensification: "Risk Intensification",
    online: "Online",
    offline: "Offline",
    queued: "queued",
    syncing: "Syncing...",
    loading: "Loading...",
    noData: "No data",
    retry: "Retry",
    escalate: "Escalate",
    issueAdvisory: "Issue Advisory",
    monitor: "Monitor",
    roadConnectivity: "Road Connectivity",
    roadAccessGood: "Good — accessible by road",
    roadAccessLimited: "Limited — single route",
    roadAccessPoor: "Poor — remote, limited",
    drainage: "Drainage Proximity",
    ruggedness: "Terrain Ruggedness",
    weatherForecast: "Weather Forecast",
    forecastTitle: "Rainfall Forecast",
    next24h: "Next 24h",
    next48h: "Next 48h",
    next72h: "Next 72h",
    rainfallExpected: "Rainfall expected",
    stormWarning: "Heavy rainfall warning",
    noStorm: "No significant rainfall",
    emergencyPriority: "Emergency Response Priority",
    priorityHigh: "High Priority",
    priorityMedium: "Medium Priority",
    priorityLow: "Low Priority",
    responseTeams: "Response Teams",
    estimatedArrival: "Est. Arrival",
    evacRoutes: "Evacuation Routes",
    shelterStatus: "Shelter Status",
  },
};

// Simple context-based i18n (no external library needed)
let currentLang: Lang = "en";

export function setLang(lang: Lang) {
  currentLang = lang;
  try { localStorage.setItem("gs_lang", lang); } catch {}
}

export function getLang(): Lang {
  try {
    const saved = localStorage.getItem("gs_lang") as Lang;
    if (saved && translations[saved]) { currentLang = saved; return saved; }
  } catch {}
  return currentLang;
}

export function t(key: keyof TranslationKeys): string {
  return translations[currentLang]?.[key] ?? translations.en[key] ?? key;
}
