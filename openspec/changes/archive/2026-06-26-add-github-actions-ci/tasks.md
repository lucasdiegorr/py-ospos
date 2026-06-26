## 1. CI Workflow

- [x] 1.1 Create `.github/workflows/ci.yml` with workflow trigger on push and pull_request to master
- [x] 1.2 Add job that checks out code and sets up Python 3.12
- [x] 1.3 Add step to install project dependencies via pip
- [x] 1.4 Add step to run `pytest --cov --cov-fail-under=90`
- [x] 1.5 Verify workflow runs and passes on the PR branch
