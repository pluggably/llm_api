# Test Reporting

This project generates a consolidated test report after running automated tests.

## Command
Run the script below from the repo root:

- scripts/generate_test_report.sh

## Outputs
Reports are written to the reports/ directory:

- reports/pytest.xml — JUnit XML report for backend pytest suite
- reports/flutter_test.json — machine-readable Flutter test report

## Notes
- The report files are intended for CI artifacts or local inspection.
- If you only need a subset, run the corresponding test command directly.
