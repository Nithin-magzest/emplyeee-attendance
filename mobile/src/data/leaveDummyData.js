export const leaveSummary = {
  month: "July",
  year: 2026,

  totalRequests: 18,
  pending: 5,
  approved: 11,
  rejected: 2,

  annualBalance: 18,
  annualTotal: 30,
};

export const leaveBalances = [
  {
    id: 1,
    title: "Casual Leave",
    short: "CL",
    total: 12,
    used: 4,
    remaining: 8,
    color: "#2563EB",
  },
  {
    id: 2,
    title: "Sick Leave",
    short: "SL",
    total: 12,
    used: 3,
    remaining: 9,
    color: "#16A34A",
  },
  {
    id: 3,
    title: "Earned Leave",
    short: "EL",
    total: 15,
    used: 5,
    remaining: 10,
    color: "#7C3AED",
  },
  {
    id: 4,
    title: "Maternity Leave",
    short: "ML",
    total: 90,
    used: 0,
    remaining: 90,
    color: "#EC4899",
  },
  {
    id: 5,
    title: "Paternity Leave",
    short: "PL",
    total: 5,
    used: 1,
    remaining: 4,
    color: "#F59E0B",
  },
  {
    id: 6,
    title: "Comp-Off",
    short: "CO",
    total: 4,
    used: 1,
    remaining: 3,
    color: "#06B6D4",
  },
];

export const leaveStats = {
  pending: 5,
  approved: 11,
  rejected: 2,
  holidays: 18,
};

export const leaveRequests = [
  {
    id: "LR001",

    employeeName: "Rahul Sharma",

    employeeId: "EMP001",

    department: "Engineering",

    designation: "Software Engineer",

    leaveType: "Casual Leave",

    startDate: "12 Jul 2026",

    endDate: "14 Jul 2026",

    days: 3,

    reason: "Family Function",

    status: "Pending",
  },

  {
    id: "LR002",

    employeeName: "Priya Reddy",

    employeeId: "EMP014",

    department: "HR",

    designation: "HR Executive",

    leaveType: "Sick Leave",

    startDate: "05 Jul 2026",

    endDate: "06 Jul 2026",

    days: 2,

    reason: "Fever",

    status: "Approved",
  },

  {
    id: "LR003",

    employeeName: "Arjun Kumar",

    employeeId: "EMP022",

    department: "Finance",

    designation: "Accountant",

    leaveType: "Earned Leave",

    startDate: "18 Jul 2026",

    endDate: "22 Jul 2026",

    days: 5,

    reason: "Vacation",

    status: "Rejected",
  },
];

export const holidays = [
  {
    id: 1,
    title: "Independence Day",
    date: "15 Aug 2026",
    day: "Saturday",
    type: "National Holiday",
  },

  {
    id: 2,
    title: "Ganesh Chaturthi",
    date: "27 Aug 2026",
    day: "Thursday",
    type: "Festival Holiday",
  },

  {
    id: 3,
    title: "Gandhi Jayanti",
    date: "02 Oct 2026",
    day: "Friday",
    type: "National Holiday",
  },

  {
    id: 4,
    title: "Diwali",
    date: "08 Nov 2026",
    day: "Sunday",
    type: "Festival Holiday",
  },
];

export const leaveTabs = [
  {
    id: "requests",
    title: "Requests",
  },
  {
    id: "holidays",
    title: "Holidays",
  },
  {
    id: "tickets",
    title: "Tickets",
  },
  {
    id: "resignations",
    title: "Resignations",
  },
];

export const leaveQuickActions = [
  {
    id: 1,
    title: "Apply",
    icon: "add-circle-outline",
  },
  {
    id: 2,
    title: "Calendar",
    icon: "calendar-outline",
  },
  {
    id: 3,
    title: "Balance",
    icon: "pie-chart-outline",
  },
  {
    id: 4,
    title: "Reports",
    icon: "bar-chart-outline",
  },
];

export const leaveLegend = [
  {
    id: 1,
    title: "Approved",
    color: "#16A34A",
  },
  {
    id: 2,
    title: "Pending",
    color: "#F59E0B",
  },
  {
    id: 3,
    title: "Rejected",
    color: "#DC2626",
  },
  {
    id: 4,
    title: "Holiday",
    color: "#2563EB",
  },
];