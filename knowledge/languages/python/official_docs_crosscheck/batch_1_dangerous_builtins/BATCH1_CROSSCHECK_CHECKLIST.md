# Batch 1 Cross-Check Checklist: Dangerous Built-ins

This checklist prepares official documentation review for the H19 advisory records. No live official documentation check is recorded here.

## 1. eval on user input
- record_id: python-advisory-eval-user-input-batch1
- term/API: eval
- current_review_status: candidate
- current_risk_level: critical
- current_execution_policy: never_execute
- official documentation target(s): https://docs.python.org/3/library/functions.html
- what must be checked: eval semantics, namespace behavior, and risk wording for string evaluation.
- safety notes to verify: user, file, network, and model text must not be evaluated as Python code.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 2. exec on model-generated code
- record_id: python-advisory-exec-model-generated-code-batch1
- term/API: exec
- current_review_status: candidate
- current_risk_level: critical
- current_execution_policy: never_execute
- official documentation target(s): https://docs.python.org/3/library/functions.html
- what must be checked: exec semantics, accepted code object/string behavior, and namespace behavior.
- safety notes to verify: model-generated code remains untrusted text unless separately reviewed by humans.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 3. compile with dynamic source
- record_id: python-advisory-compile-dynamic-source-batch1
- term/API: compile
- current_review_status: candidate
- current_risk_level: critical
- current_execution_policy: never_execute
- official documentation target(s): https://docs.python.org/3/library/functions.html
- what must be checked: compile modes, returned code object behavior, and relationship to later eval/exec use.
- safety notes to verify: dynamic source from user, model, file, or network input must remain non-executed data.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 4. dynamic import with user-controlled module name
- record_id: python-advisory-dynamic-import-user-module-batch1
- term/API: import / __import__ / importlib.import_module
- current_review_status: candidate
- current_risk_level: critical
- current_execution_policy: never_execute
- official documentation target(s): https://docs.python.org/3/library/functions.html
- what must be checked: built-in import behavior, import system trust boundaries, and whether importlib documentation must be added in a later pass.
- safety notes to verify: module names from users, files, network data, or model output require an explicit allowlist.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 5. open with user-controlled path and write mode
- record_id: python-advisory-open-user-path-write-mode-batch1
- term/API: open
- current_review_status: candidate
- current_risk_level: high
- current_execution_policy: advisory_only_no_execution
- official documentation target(s): https://docs.python.org/3/library/functions.html, https://docs.python.org/3/library/pathlib.html
- what must be checked: open modes, truncation/overwrite implications, path handling assumptions, and pathlib containment guidance.
- safety notes to verify: write paths require boundary checks, explicit mode validation, and overwrite review.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 6. input passed into eval/exec or shell command
- record_id: python-advisory-input-to-dynamic-execution-batch1
- term/API: input
- current_review_status: candidate
- current_risk_level: critical
- current_execution_policy: never_execute
- official documentation target(s): https://docs.python.org/3/library/functions.html, https://docs.python.org/3/library/subprocess.html
- what must be checked: input return type, untrusted text handling, and interaction with dynamic execution or shell invocation guidance.
- safety notes to verify: raw input must be parsed as data and never treated as Python source or shell syntax.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 7. globals/locals used for dynamic namespace mutation
- record_id: python-advisory-globals-locals-namespace-mutation-batch1
- term/API: globals / locals
- current_review_status: candidate
- current_risk_level: high
- current_execution_policy: advisory_only_no_execution
- official documentation target(s): https://docs.python.org/3/library/functions.html
- what must be checked: globals and locals return values, namespace behavior, and limits around mutation semantics.
- safety notes to verify: explicit application-owned dictionaries should replace namespace mutation.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 8. getattr/setattr/delattr with user-controlled attribute name
- record_id: python-advisory-dynamic-attribute-user-name-batch1
- term/API: getattr / setattr / delattr
- current_review_status: candidate
- current_risk_level: high
- current_execution_policy: advisory_only_no_execution
- official documentation target(s): https://docs.python.org/3/library/functions.html
- what must be checked: dynamic attribute read, mutation, and deletion behavior.
- safety notes to verify: attribute names must come from explicit allowlists, with mutation and deletion reviewed separately.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 9. pickle.load / pickle.loads on untrusted data
- record_id: python-advisory-pickle-untrusted-data-batch1
- term/API: pickle.load / pickle.loads
- current_review_status: candidate
- current_risk_level: critical
- current_execution_policy: never_execute
- official documentation target(s): https://docs.python.org/3/library/pickle.html
- what must be checked: pickle loading behavior and official security warning language.
- safety notes to verify: untrusted pickle data must not be loaded; safer interchange formats should be used for untrusted data.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed

## 10. subprocess.run with shell=True and user/model input
- record_id: python-advisory-subprocess-shell-true-user-input-batch1
- term/API: subprocess.run
- current_review_status: candidate
- current_risk_level: critical
- current_execution_policy: never_execute
- official documentation target(s): https://docs.python.org/3/library/subprocess.html, https://docs.python.org/3/library/os.html
- what must be checked: shell behavior, argument list behavior, timeout/check recommendations, and os.system/os.popen comparison if relevant.
- safety notes to verify: untrusted user or model text must not be composed into shell command strings.
- discrepancy_found: unchecked
- reviewer: pending
- review_date: pending
- next_status_recommendation: remain_candidate
- do_not_promote_reason: official docs check and human review not completed
