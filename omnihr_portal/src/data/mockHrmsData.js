export const MOCK_COMPANY = {
  name: "OmniHR Global Technologies",
  subdomain: "global.omnihr.com",
  totalEmployees: 60847,
  newHiresYtd: 1247,
  retentionRatePct: 94.2,
  annualPayrollUsd: 4200000000,
  entities: [
    { code: "US_INC", name: "US Inc. (Delaware)", country: "United States", currency: "USD", symbol: "$" },
    { code: "UK_LTD", name: "UK Ltd. (London)", country: "United Kingdom", currency: "GBP", symbol: "£" },
    { code: "SG_PTE", name: "SG Pte. (Singapore)", country: "Singapore", currency: "SGD", symbol: "S$" },
    { code: "DE_GMBH", name: "DE GmbH (Munich)", country: "Germany", currency: "EUR", symbol: "€" },
    { code: "IN_PVT", name: "IN Pvt Ltd (Bengaluru)", country: "India", currency: "INR", symbol: "₹" }
  ]
};

export const MOCK_EMPLOYEES = [
  {
    id: "EMP-1001",
    name: "Dr. Evelyn Vance",
    role: "VP of Distributed Infrastructure",
    department: "Core Platform Engineering",
    email: "evelyn.vance@omnihr.com",
    avatar: "EV",
    location: "New York, US",
    entity: "US Inc. (Delaware)",
    salary: 380000,
    currency: "USD",
    joinDate: "2020-03-15",
    status: "ACTIVE",
    attritionRisk: "LOW",
    device: { model: "MacBook Pro 16\" M3 Max", serial: "C02G188XMD6M", status: "ENROLLED_MDM", assignedDate: "2023-11-01" },
    directReports: 8,
    manager: "CEO Office"
  },
  {
    id: "EMP-1002",
    name: "Marcus Sterling",
    role: "Principal SecOps Architect",
    department: "Security Operations",
    email: "marcus.sterling@omnihr.com",
    avatar: "MS",
    location: "London, UK",
    entity: "UK Ltd. (London)",
    salary: 290000,
    currency: "GBP",
    joinDate: "2021-06-01",
    status: "ACTIVE",
    attritionRisk: "LOW",
    device: { model: "ThinkPad P1 Gen 6", serial: "PF-2X98L1", status: "ENROLLED_MDM", assignedDate: "2022-05-12" },
    directReports: 4,
    manager: "Dr. Evelyn Vance"
  },
  {
    id: "EMP-1003",
    name: "Priya Sharma",
    role: "Staff ML Research Engineer",
    department: "AI & Data Science",
    email: "priya.sharma@omnihr.com",
    avatar: "PS",
    location: "Singapore, SG",
    entity: "SG Pte. (Singapore)",
    salary: 240000,
    currency: "SGD",
    joinDate: "2022-01-10",
    status: "ACTIVE",
    attritionRisk: "MEDIUM",
    device: { model: "MacBook Pro 14\" M3 Pro", serial: "C02H599PK12", status: "ENROLLED_MDM", assignedDate: "2024-01-15" },
    directReports: 0,
    manager: "Dr. Evelyn Vance"
  },
  {
    id: "EMP-1004",
    name: "Kaelen Rivera",
    role: "Enterprise AE — EMEA",
    department: "Global Sales",
    email: "kaelen.rivera@omnihr.com",
    avatar: "KR",
    location: "Frankfurt, DE",
    entity: "DE GmbH (Munich)",
    salary: 210000,
    currency: "EUR",
    joinDate: "2019-11-20",
    status: "ON_LEAVE",
    attritionRisk: "HIGH",
    device: { model: "Dell XPS 15", serial: "DL-994200", status: "ENROLLED_MDM", assignedDate: "2021-02-10" },
    directReports: 0,
    manager: "Hannah Abbott"
  },
  {
    id: "EMP-1005",
    name: "Sarah Jenkins",
    role: "Senior Director of People Operations",
    department: "Human Resources",
    email: "sarah.jenkins@omnihr.com",
    avatar: "SJ",
    location: "New York, US",
    entity: "US Inc. (Delaware)",
    salary: 265000,
    currency: "USD",
    joinDate: "2018-08-04",
    status: "ACTIVE",
    attritionRisk: "LOW",
    device: { model: "MacBook Air 15\" M2", serial: "C02F100MK99", status: "ENROLLED_MDM", assignedDate: "2023-08-20" },
    directReports: 6,
    manager: "CEO Office"
  }
];

export const MOCK_PAYROLL = {
  cycle: "July 2026",
  status: "READY_FOR_DISBURSEMENT",
  runs: [
    { entity: "US Inc. (Delaware)", gross: 14200000, tax: 3550000, net: 10650000, variance: 1.2, status: "AUDITED" },
    { entity: "UK Ltd. (London)", gross: 8400000, tax: 2100000, net: 6300000, variance: 6.2, status: "VARIANCE_FLAGGED" },
    { entity: "SG Pte. (Singapore)", gross: 5100000, tax: 765000, net: 4335000, variance: 0.4, status: "AUDITED" },
    { entity: "DE GmbH (Munich)", gross: 6800000, tax: 2720000, net: 4080000, variance: -0.8, status: "AUDITED" },
    { entity: "IN Pvt Ltd (Bengaluru)", gross: 3200000, tax: 640000, net: 2560000, variance: 2.1, status: "CALCULATING" }
  ],
  ewaQueue: [
    { id: "EWA-501", empName: "Alex Rivera", accruedSalary: 6400, requestedAmount: 1500, fee: 2.99, status: "APPROVED_INSTANT" },
    { id: "EWA-502", empName: "Elena Rostova", accruedSalary: 8200, requestedAmount: 2000, fee: 2.99, status: "PENDING_REVIEW" }
  ]
};

export const MOCK_ATTENDANCE = {
  todayHeatmap: [
    { location: "New York HQ", inOffice: 62, remote: 32, leave: 6, total: 18400 },
    { location: "London Hub", inOffice: 58, remote: 36, leave: 6, total: 12100 },
    { location: "Singapore Tech Hub", inOffice: 74, remote: 22, leave: 4, total: 9400 },
    { location: "Munich R&D", inOffice: 52, remote: 42, leave: 6, total: 6800 },
    { location: "Bengaluru Dev Center", inOffice: 81, remote: 15, leave: 4, total: 14147 }
  ],
  rosterShifts: [
    { empId: "EMP-1001", empName: "Dr. Evelyn Vance", shift: "EMEA Core (09:00 - 17:00)", status: "PUNCHED_IN", lat: 40.7128, lon: -74.0060 },
    { empId: "EMP-1002", empName: "Marcus Sterling", shift: "UK Night Guard (16:00 - 00:00)", status: "PUNCHED_IN", lat: 51.5074, lon: -0.1278 }
  ]
};

export const MOCK_ATS_CANDIDATES = [
  { id: "C-901", name: "Alexander Wright", role: "Sr. Staff Distributed Engineer", stage: "INTERVIEW", matchScore: 96, expYears: 12 },
  { id: "C-902", name: "Sophia Chen", role: "Director of AI Ethics & Policy", stage: "OFFER", matchScore: 98, expYears: 15 },
  { id: "C-903", name: "Dimitri Rostov", role: "Lead Security Automation Engineer", stage: "SCREENED", matchScore: 92, expYears: 8 },
  { id: "C-904", name: "Hannah Abbott", role: "VP of Global Enterprise Sales", stage: "HIRED", matchScore: 95, expYears: 18 }
];

export const MOCK_PERFORMANCE = {
  nineBox: [
    { id: "E1", name: "Dr. Evelyn Vance", role: "VP Infra", quadrant: "STAR", perf: 3, pot: 3 },
    { id: "E2", name: "Marcus Sterling", role: "SecOps Lead", quadrant: "HIGH_PERFORMER", perf: 3, pot: 2 },
    { id: "E3", name: "Priya Sharma", role: "Staff ML Eng", quadrant: "HIGH_POTENTIAL", perf: 2, pot: 3 },
    { id: "E4", name: "Kaelen Rivera", role: "Enterprise AE", quadrant: "CORE_PERFORMER", perf: 2, pot: 2 }
  ],
  okrs: [
    { title: "Achieve 99.999% Infrastructure Uptime", owner: "Dr. Evelyn Vance", progress: 98, category: "Engineering" },
    { title: "Reduce SOC 2 Remediation Time to < 15 mins", owner: "Marcus Sterling", progress: 92, category: "Security" }
  ]
};

export const MOCK_AUTOMATIONS = [
  { id: "AUTO-101", trigger: "On Employee Hire (Rippling style)", action: "Auto-grant Slack, GitHub, Figma & order MacBook Pro", status: "ACTIVE", executions: 1247 },
  { id: "AUTO-102", trigger: "Leave Request Submitted", action: "Verify >80% team capacity; auto-approve if valid", status: "ACTIVE", executions: 8940 },
  { id: "AUTO-103", trigger: "Overtime > 48h/week", action: "Flag HRBP & trigger automated rest window notification", status: "ACTIVE", executions: 340 }
];
