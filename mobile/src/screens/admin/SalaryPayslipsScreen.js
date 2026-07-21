import React, { useMemo, useState } from "react";

import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  Alert,
} from "react-native";

import AdminHeader from "../../components/admin/AdminHeader";

import SalaryHeader from "../../components/admin/salary/SalaryHeader";
import SalarySearchBar from "../../components/admin/salary/SalarySearchBar";
import MonthYearSelector from "../../components/admin/salary/MonthYearSelector";
import PayrollSummaryCard from "../../components/admin/salary/PayrollSummaryCard";
import SalaryStatsGrid from "../../components/admin/salary/SalaryStatsGrid";
import PayrollActionButtons from "../../components/admin/salary/PayrollActionButtons";
import SalaryEmployeeCard from "../../components/admin/salary/SalaryEmployeeCard";
import SalaryRulesCard from "../../components/admin/salary/SalaryRulesCard";
import PayrollActionSheet from "../../components/admin/salary/PayrollActionSheet";
import EmployeeSalaryBottomSheet from "../../components/admin/salary/EmployeeSalaryBottomSheet";
import EmptySalaryState from "../../components/admin/salary/EmptySalaryState";

import SALARY_THEME from "../../constants/salaryTheme";

import {
  salaryOverview,
  employeeSalaryData,
  salaryRules,
} from "../../data/salaryDummyData";

export default function SalaryPayslipsScreen() {
  const [search, setSearch] = useState("");

  const [selectedMonth] = useState(
    salaryOverview.month
  );

  const [selectedYear] = useState(
    salaryOverview.year
  );

  const [actionSheetVisible, setActionSheetVisible] =
    useState(false);

  const [employeeSheetVisible, setEmployeeSheetVisible] =
    useState(false);

  const [selectedEmployee, setSelectedEmployee] =
    useState(null);

  const employees = useMemo(() => {
    if (!search.trim()) {
      return employeeSalaryData;
    }

    const keyword = search.toLowerCase();

    return employeeSalaryData.filter(
      (employee) =>
        employee.name
          .toLowerCase()
          .includes(keyword) ||
        employee.employeeId
          .toLowerCase()
          .includes(keyword) ||
        employee.department
          .toLowerCase()
          .includes(keyword)
    );
  }, [search]);

  const handleGeneratePayroll = () => {
    Alert.alert(
      "Generate Payroll",
      "Payroll generation will be implemented with backend integration."
    );
  };

  const handleExport = () => {
    Alert.alert(
      "Export",
      "Excel export will be implemented."
    );
  };

  const handleEmail = () => {
    Alert.alert(
      "Email Payslips",
      "Email functionality will be implemented."
    );
  };

  const handlePrint = () => {
    Alert.alert(
      "Print",
      "Print functionality will be implemented."
    );
  };

  const handleLockPayroll = () => {
    Alert.alert(
      "Lock Payroll",
      "Payroll locking will be implemented."
    );
  };

  const handleViewEmployee = (employee) => {
    setSelectedEmployee(employee);
    setEmployeeSheetVisible(true);
  };

  const handleDownloadEmployee = () => {
    Alert.alert(
      "Download",
      "Payslip download will be implemented."
    );
  };

  const handleEmailEmployee = () => {
    Alert.alert(
      "Email",
      "Employee payslip email will be implemented."
    );
  };

  const handlePrintEmployee = () => {
    Alert.alert(
      "Print",
      "Employee payslip printing will be implemented."
    );
  };

  return (
    <SafeAreaView style={styles.container}>

      <AdminHeader title="Salary & Payslips" />

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
              <SalaryHeader
          month={selectedMonth}
          year={selectedYear}
          onSettingsPress={() =>
            Alert.alert(
              "Payroll Settings",
              "Payroll settings screen will be added."
            )
          }
        />

        <SalarySearchBar
          value={search}
          onChangeText={setSearch}
          onClear={() => setSearch("")}
        />

        <MonthYearSelector
          selectedMonth={selectedMonth}
          selectedYear={selectedYear}
          onMonthPress={() =>
            Alert.alert(
              "Month",
              "Month selector will be implemented."
            )
          }
          onYearPress={() =>
            Alert.alert(
              "Year",
              "Year selector will be implemented."
            )
          }
          onGeneratePress={handleGeneratePayroll}
        />

        <PayrollSummaryCard
          month={selectedMonth}
          year={selectedYear}
          totalEmployees={
            salaryOverview.totalEmployees
          }
          totalGross={
            salaryOverview.totalGross
          }
          totalNet={
            salaryOverview.totalNetPay
          }
          totalDeductions={
            salaryOverview.totalDeductions
          }
          payrollStatus={
            salaryOverview.payrollStatus
          }
          onGeneratePayroll={
            handleGeneratePayroll
          }
        />

        <SalaryStatsGrid
          totalEmployees={
            salaryOverview.totalEmployees
          }
          grossSalary={
            salaryOverview.totalGross
          }
          deductions={
            salaryOverview.totalDeductions
          }
          netSalary={
            salaryOverview.totalNetPay
          }
        />

        <PayrollActionButtons
          onGenerate={
            handleGeneratePayroll
          }
          onExport={handleExport}
          onEmail={handleEmail}
          onMore={() =>
            setActionSheetVisible(true)
          }
        />
                {employees.length === 0 ? (

          <EmptySalaryState
            title="No Employees Found"
            subtitle="Try searching with another employee name or generate payroll after adding employees."
            buttonText="Generate Payroll"
            onPress={handleGeneratePayroll}
          />

        ) : (

          <View style={styles.employeeSection}>

            {employees.map((employee) => (

              <SalaryEmployeeCard
                key={employee.id}
                employee={employee}
                onView={handleViewEmployee}
                onDownload={handleDownloadEmployee}
                onEmail={handleEmailEmployee}
              />

            ))}

          </View>

        )}

        <SalaryRulesCard
          rules={salaryRules}
        />

        <View style={{ height: 30 }} />

      </ScrollView>

      {/* Payroll Actions Bottom Sheet */}

      <PayrollActionSheet
        visible={actionSheetVisible}
        onClose={() =>
          setActionSheetVisible(false)
        }
        onGenerate={() => {
          setActionSheetVisible(false);
          handleGeneratePayroll();
        }}
        onExport={() => {
          setActionSheetVisible(false);
          handleExport();
        }}
        onPrint={() => {
          setActionSheetVisible(false);
          handlePrint();
        }}
        onEmail={() => {
          setActionSheetVisible(false);
          handleEmail();
        }}
        onLock={() => {
          setActionSheetVisible(false);
          handleLockPayroll();
        }}
      />

      {/* Employee Payslip Bottom Sheet */}

      <EmployeeSalaryBottomSheet
        visible={employeeSheetVisible}
        employee={selectedEmployee}
        onClose={() => {
          setEmployeeSheetVisible(false);
          setSelectedEmployee(null);
        }}
        onDownload={handleDownloadEmployee}
        onEmail={handleEmailEmployee}
        onPrint={handlePrintEmployee}
      />

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({  container: {
    flex: 1,
    backgroundColor: SALARY_THEME.colors.background,
  },

  scrollView: {
    flex: 1,
  },

  content: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 40,
  },

  employeeSection: {
    marginTop: 4,
    marginBottom: 20,
  },
});