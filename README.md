# JIRA Ticket Analyzer for Embedded Systems

## Project Overview
This tool analyzes JIRA tickets for the Embedded Systems team at u-blox.
- Classified the ticket type (ROM/FW releases, bug fixes, etc.)
- Analyse that is complied with DoD
- Generate a structured acceptance criteria
- Identify missing information

## Definition of Done (DoD)

### General feature development DoD
1. Code changes are reviewed and approved
2. Documentation (Platform User Manual/Confluence/ESHDocs ) is updated
3. Tests (Unittests and/or HWSW tests) are written and passing
4. Changes are verified in the target environment
5. Regression tests show no regressions

### Release (ROM/FW) DoD
1. Pre-TO testing completed in FPGA or ASIC
2. All test cases documented and executed
3. Release notes and version number updated
4. Binary files generated and verified
5. Simulation tests passed (if applicable)

### Bug Fix DoD
1. Root cause identified and documented
2. Fix verified in the target environment
3. Test case added to prevent regression
4. Fix documented in release notes
5. Customer communication prepared (if customer-reported)

### Verification and Bring-up DoD
1. Results recorded in the ticket. THis can be in the form of screenshot, log files, etc.
2. Issues found are documented in JIRA
3. Test coverage metrics met
4. Hardware/software configurations documented

### Tool Update DoD
1. The build script or Tool such as an otp-html-tool, crypto tools, ubtools/, DevOps or RTGUT, is worked on
2. The new functionality is verified by running a test, with a screenshot
3. Documentation updated
4. Backward compatibility verified
5. User guide updated (if applicable)

### RMA (Return material authorization) DoD
1. Customers Issue reproduced and documented
2. Root cause analysis completed and reported in the ticket
3. Fix found and verified. A screenshot or a file attached to the ticket
4. Customer communication prepared
5. Prevention measures documented

### Investigation/Concept Work DoD
1. Investigative or proof of concept work documented
2. Findings documented in an empirical measure (time taken, number of iterations, etc.)
3. Recommendations provided
4. Next steps identified
5. Resource requirements estimated

## Common Acronyms
- **TO**: Tape Out - The final stage of chip design when the design is sent for manufacturing
- **EIP**: Embedded IP - Intellectual Property blocks used in chip design
- **ROM**: Read-Only Memory
- **FW**: Firmware
- **RMA**: Return Merchandise Authorization
- **DoD**: Definition of Done
- **PRD**: Product Requirements Document
- **DV**: Design Verification
- **RTL**: Register Transfer Level
- **SoC**: System on Chip
- **HAL**: Hardware Abstraction Layer


## Usage
```bash
python main.py <JIRA_TICKET_NUMBER>
```

Example:
```bash
python main.py 1281
```

## Output Format
The analyzer provides output in the following structured format:

```
==================================================
Analysis of TICKET-NUMBER
==================================================
**Ticket Type:**
[Ticket classification]

**DoD Analysis:**
[Analysis of DoD compliance]

**Proposed Acceptance Criteria:**
1. [Criterion]
   - Testing method: [Verification]
   - Done when: [Completion state]

**Missing Information:**
[List of unclear or missing details]
==================================================
```

## Environment Setup
1. Create a `.env` file with:
   ```
   OPENAI_API_KEY=your_key_here
   JIRA_SERVER=your_jira_server
   JIRA_EMAIL=your_email
   JIRA_API_TOKEN=your_api_token
   ```
2. Install requirements:
   ```
   pip install -r requirements.txt
   ```

## Contributing
When contributing to this project:
1. Follow Python PEP 8 style guide
2. Add tests for new features
3. Update documentation as needed
4. Maintain backward compatibility

// how to download crewai
// powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
// Add to cmd and powershell PATH
// uv tool install crewai
// uv tool list
// crewai install
// crewai run
// pip install crewai
// python -c "from crewai import Agent, Task, Crew; print('CrewAI is installed!')"
