*** Settings ***
Resource          data_formats/formats_resource.robot

*** Variables ***
${PARSING}            ${DATADIR}/parsing
${SUITE DIR}          %{TEMPDIR}/tmp

*** Test Cases ***
Directory Containing No Test Cases
    Run tests and check error
    ...    ${PARSING}/notests
    ...    Suite 'Notests' contains no tests or tasks.

File Containing No Test Cases
    Run tests and check error
    ...    ${PARSING}/empty_testcase_table.robot
    ...    Suite 'Empty Testcase Table' contains no tests or tasks.

Empty File
    Run tests and check error
    ...    ${ROBOTDIR}/empty.robot
    ...    Suite 'Empty' contains no tests or tasks.

Multisource Containing Empty File
    Run tests and check error
    ...    ${ROBOTDIR}/empty.robot ${ROBOTDIR}/sample.robot
    ...    Suite 'Empty' contains no tests or tasks.

Multisource With Empty Directory
    Run tests and check error
    ...    ${ROBOTDIR}/sample.robot ${PARSING}/notests
    ...    Suite 'Notests' contains no tests or tasks.

Multisource Containing Empty File With Non-standard Extension
    Run tests and check error
    ...    ${PARSING}/unsupported.log ${ROBOTDIR}/sample.robot
    ...    Suite 'Unsupported' contains no tests or tasks.

File With Invalid Encoding
    Run tests and check parsing error
    ...    ${PARSING}/invalid_encoding/invalid_encoding.robot
    ...    UnicodeDecodeError: .*
    ...    ${PARSING}/invalid_encoding/invalid_encoding.robot

Directory Containing File With Invalid Encoding
    Run tests and check parsing error
    ...    ${PARSING}/invalid_encoding/
    ...    UnicodeDecodeError: .*
    ...    ${PARSING}/invalid_encoding/invalid_encoding.robot

If with else after else
    Run tests and check parsing error
    ...    ${PARSING}/if/else_after_else.robot
    ...    .* Invalid second ELSE detected
    ...    ${PARSING}/if/else_after_else.robot

If with else if after else
    Run tests and check parsing error
    ...    ${PARSING}/if/else_if_after_else.robot
    ...    .* Invalid ELSE IF detected after ELSE
    ...    ${PARSING}/if/else_if_after_else.robot

If for else if parsing
    Run tests and check parsing error
    ...    ${PARSING}/if/for_else_invalid.robot
    ...    .* Invalid ELSE IF detected after ELSE
    ...    ${PARSING}/if/for_else_invalid.robot

If with empty if
    Run tests and check parsing error
    ...    ${PARSING}/if/empty_if.robot
    ...    .* Empty block detected
    ...    ${PARSING}/if/empty_if.robot

If with empty else
    Run tests and check parsing error
    ...    ${PARSING}/if/empty_else.robot
    ...    .* Empty block detected
    ...    ${PARSING}/if/empty_else.robot

If with empty else_if
    Run tests and check parsing error
    ...    ${PARSING}/if/empty_else_if.robot
    ...    .* Empty block detected
    ...    ${PARSING}/if/empty_else_if.robot

If without condition
    Run tests and check parsing error
    ...    ${PARSING}/if/if_without_condition.robot
    ...    .* IF without condition
    ...    ${PARSING}/if/if_without_condition.robot

If with many conditions
    Run tests and check parsing error
    ...    ${PARSING}/if/if_with_many_conditions.robot
    ...    .* IF with multiple conditions
    ...    ${PARSING}/if/if_with_many_conditions.robot

If without end
    Run tests and check error
    ...    ${PARSING}/if/if_without_end.robot
    ...    .*IF has no closing 'END'.

If with wrong case
    Run tests and check parsing error
    ...    ${PARSING}/if/if_wrong_case.robot
    ...    .* IF must be typed in upper case
    ...    ${PARSING}/if/if_wrong_case.robot

Else if without condition
    Run tests and check parsing error
    ...    ${PARSING}/if/else_if_without_condition.robot
    ...    .* ELSE IF without condition
    ...    ${PARSING}/if/else_if_without_condition.robot

Else if with multiple conditions
    Run tests and check parsing error
    ...    ${PARSING}/if/else_if_with_many_conditions.robot
    ...    .* ELSE IF with multiple conditions
    ...    ${PARSING}/if/else_if_with_many_conditions.robot

Else with a condition
    Run tests and check parsing error
    ...    ${PARSING}/if/else_with_condition.robot
    ...    .* ELSE with a condition
    ...    ${PARSING}/if/else_with_condition.robot

Multisource Containing File With Invalid Encoding
    Run tests and check parsing error
    ...    ${PARSING}/invalid_encoding/invalid_encoding.robot ${PARSING}/invalid_encoding/a_valid_file.robot
    ...    UnicodeDecodeError: .*
    ...    ${PARSING}/invalid_encoding/invalid_encoding.robot

File without read permission
    [Tags]    no-windows
    [Setup]    Create test data without permissions    ${SUITE DIR}/sample.robot
    Run tests and check parsing error
    ...    ${SUITE DIR}/sample.robot
    ...    (IOError|PermissionError): .*
    ...    ${SUITE DIR}/sample.robot
    [Teardown]    Remove test data without permissions    ${SUITE DIR}/sample.robot

Directory without read permission
    [Tags]    no-windows
    [Setup]    Create test data without permissions    ${SUITE DIR}
    Run tests and check parsing error
    ...    ${SUITE DIR}
    ...    (OSError|PermissionError): .*
    ...    ${SUITE DIR}
    ...    Reading directory
    [Teardown]    Remove test data without permissions    ${SUITE DIR}

*** Keywords ***
Run tests and check error
    [Arguments]    ${paths}   ${error}
    ${result}=    Run Tests Without Processing Output    ${EMPTY}    ${paths}
    Should be equal    ${result.rc}    ${252}
    Stderr Should Match Regexp    \\[ ERROR \\] ${error}${USAGE_TIP}

Run tests and check parsing error
    [Arguments]    ${paths}    ${error}    ${path}    ${prefix}=Parsing
    ${path}=    Normalize path    ${path}
    ${path}=    Regexp escape    ${path}
    Run tests and check error    ${paths}    ${prefix} '${path}' failed: ${error}

Create test data without permissions
    [Arguments]    ${remove permissions}
    Create directory    ${SUITE DIR}
    Copy file   ${ROBOTDIR}/sample.robot   ${SUITE DIR}
    Remove permissions    ${remove permissions}

Remove test data without permissions
    [Arguments]    ${remove permissions}
    Set read write execute      ${remove permissions}
    Remove directory    ${SUITE DIR}    recursive=True
