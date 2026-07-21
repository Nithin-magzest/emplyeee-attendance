export const salaryOverview = {
  month: "July",
  year: "2026",

  totalEmployees: 2,

  totalGross: 0,

  totalDeductions: 0,

  totalNetPay: 0,

  payrollStatus: "Draft",
};

export const employeeSalaryData = [
  {
    id: "EMP001",

    employeeId: "GDZ001",

    name: "Emma Wilson",

    email: "employee@gmail.com",

    department: "Engineering",

    designation: "Software Engineer",

    avatar: "",

    dailyRate: 0,

    workDays: 8,

    attendance: {
      full: 0,
      late: 0,
      half: 0,
      absent: 8,
    },

    earnings: {
      fullDayPay: 0,
      latePay: 0,
      halfDayPay: 0,
      incentive: 0,
    },

    deductions: {
      late: 0,
      halfDay: 0,
      absent: 0,
    },

    grossSalary: 0,

    netSalary: 0,

    payrollStatus: "Pending",
  },

  {
    id: "EMP002",

    employeeId: "GDZ002",

    name: "John David",

    email: "employee@gmail.com",

    department: "Sales",

    designation: "Sales Executive",

    avatar: "",

    dailyRate: 0,

    workDays: 8,

    attendance: {
      full: 0,
      late: 0,
      half: 0,
      absent: 8,
    },

    earnings: {
      fullDayPay: 0,
      latePay: 0,
      halfDayPay: 0,
      incentive: 0,
    },

    deductions: {
      late: 0,
      halfDay: 0,
      absent: 0,
    },

    grossSalary: 0,

    netSalary: 0,

    payrollStatus: "Pending",
  },
];

export const salaryRules = [
  {
    id: 1,

    type: "success",

    title: "Full Day",

    description:
      "Login before 9:00 AM and logout after 6:00 PM. 100% salary is paid.",
  },

  {
    id: 2,

    type: "warning",

    title: "Late Login",

    description:
      "Login after 9:00 AM. 10% deduction from daily salary.",
  },

  {
    id: 3,

    type: "warning",

    title: "Half Day",

    description:
      "Login after 1:00 PM or logout before 1:00 PM. 50% salary deduction.",
  },

  {
    id: 4,

    type: "danger",

    title: "Absent",

    description:
      "No attendance recorded. Full day salary deduction.",
  },

  {
    id: 5,

    type: "info",

    title: "Holiday",

    description:
      "Public holidays are treated as paid working days.",
  },

  {
    id: 6,

    type: "approved",

    title: "Approved Leave",

    description:
      "Approved leave is excluded from working days calculation.",
  },
];

export const payrollActions = [
  {
    id: 1,
    title: "Generate Payroll",
    icon: "wallet-outline",
    color: "#2563EB",
  },

  {
    id: 2,
    title: "Export Excel",
    icon: "download-outline",
    color: "#16A34A",
  },

  {
    id: 3,
    title: "Print",
    icon: "print-outline",
    color: "#F59E0B",
  },

  {
    id: 4,
    title: "Email Payslips",
    icon: "mail-outline",
    color: "#8B5CF6",
  },

  {
    id: 5,
    title: "Lock Payroll",
    icon: "lock-closed-outline",
    color: "#DC2626",
  },
];

export const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const years = [
  "2024",
  "2025",
  "2026",
  "2027",
];