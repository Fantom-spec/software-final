# Assessment 8 - Testing (Room Allocation module)

| File | Content |
|---|---|
| `docs/TESTING_PROCEDURE.md` | step-by-step manual and automated testing procedure |
| `manual_testing/manual_test_cases.csv` / `.md` | manual cases (scenario, preconditions, steps, input data, expected result) |
| `manual_testing/Manual_Test_Document.docx` / `.pdf` | the manual test document: every case with steps, expected result, a reference screenshot of the expected screen and a blank result box (generated; status NOT EXECUTED until results are recorded) |
| `manual_testing/reference_screenshots/` | script-captured screenshots of the expected state of each case (not tester evidence) |
| `manual_testing/manual_test_execution.csv` | **results sheet - to be filled by the person who executes the cases** (currently all *Not Executed*) |
| `manual_testing/manual_test_report.md` | generated from the results sheet |
| `results/` | `junit.xml`, `coverage.xml`, `pytest_output.txt`, `environment.txt`, `run_info.json`, `test_metrics.md` (generated) |
| `defects.csv`, `defect_log.md` | defect register (source) and generated log |
| `requirements_traceability.md` | requirements to tests/manual cases (generated) |
| `final_test_report.md` | test report (generated from the artifacts) |

Tests live in `../tests/`; the application in `../hms_app/` (shared with Assessment 9).
