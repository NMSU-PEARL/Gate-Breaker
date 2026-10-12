# Netlist-to-RTL Workflow Diagram

This document provides a comprehensive visualization of the netlist-to-RTL workflow in the gate_breaker project.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       NETLIST-TO-RTL COMPLETE WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐                  (ONE-TIME SETUP)
│ dataset_spec-to-rtl     │
│                         │                  ┌───────────────────────────────┐
│ Prob*_ref.sv            │───┐             │ scripts/generate-netlist-dataset │
│ (Original RTL design)   │   │             │                               │
│ Prob*_test.sv           │   └──────────▶ │ - Synthesizes RTL to netlists  │
│ (Test files)            │                 │ - Creates prompt files        │
└─────────────────────────┘                 │ - Copies test files           │
                                            └───────────┬───────────────────┘
                                                        │
                                                        ▼
                                            ┌───────────────────────────────┐
                                            │ dataset_netlist-to-rtl        │
                                            │                               │
                                            │ Prob*_netlist.v               │
                                            │ (Synthesized gate-level)      │
                                            │ Prob*_prompt.txt              │
                                            │ (LLM prompts with netlists)   │
                                            │ Prob*_ref.sv                  │
                                            │ (Original RTL - copied)       │
                                            │ Prob*_test.sv                 │
                                            │ (Test files - copied)         │
                                            └───────────┬───────────────────┘
                                                        │
                                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            CONFIGURATION (Step 2)                              │
└───────────────────────────────────────────────────────────────────────────────┘
                                                        │
                         ┌──────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────┐
│ ./configure --with-task=netlist-to-rtl       │
│   --with-model=gpt-4 --with-samples=3        │
└────────────────────────┬─────────────────────┘
                         │
                         │    ┌──────────────────────────┐
                         │    │ configure.ac             │
                         │    │                          │
                         ├───▶│ - Processes parameters   │
                         │    │ - Sets task=netlist-to-rtl│
                         │    │ - Sets dataset directory  │
                         │    │ - Generates problems list │
                         │    └──────────────┬───────────┘
                         │                   │
                         ▼                   ▼
┌────────────────────────────────┐  ┌────────────────────────┐
│ problems.mk                    │  │ samples.mk             │
│                                │  │                        │
│ problems = \                   │  │ Prob009_popcount3_num_samples = 3 │
│   Prob009_popcount3 \         │  │ Prob017_mux2to1v_num_samples = 3  │
│   Prob017_mux2to1v \          │  │ ...                     │
│   ...                          │  │                        │
└─────────────────┬──────────────┘  └───────────┬────────────┘
                  │                             │
                  └──────────────┬──────────────┘
                                 │
                  ┌──────────────▼──────────────┐
                  │ Makefile                    │
                  │ (generated from Makefile.in)│
                  │                            │
                  │ - Sets task=netlist-to-rtl  │
                  │ - Points to dataset dir     │
                  │ - Defines build targets     │
                  └──────────────┬──────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           RTL GENERATION (Step 3)                              │
└───────────────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ make sv-generate                                                │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                  ┌──────────────▼──────────────┐
                  │ scripts/sv-generate         │
                  │                            │
                  │ For each problem & sample:  │
                  │ - Reads netlist-to-rtl prompt│
                  │ - Runs LLM inference        │
                  │ - Extracts generated RTL    │
                  └──────────────┬──────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Output Directory: Prob009_popcount3/                        │
│                                                             │
│ Prob009_popcount3_sample01.sv        (LLM-generated RTL)    │
│ Prob009_popcount3_sample01-sv-generate.log  (Generation log)│
│ Prob009_popcount3_sample02.sv                               │
│ Prob009_popcount3_sample02-sv-generate.log                  │
│ Prob009_popcount3_sample03.sv                               │
│ Prob009_popcount3_sample03-sv-generate.log                  │
└─────────────────────────────────┬───────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            TESTING (Step 4)                                    │
└───────────────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ make sv-iv-test                                                 │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                  ┌──────────────▼──────────────────────────────────┐
                  │ For each problem and sample:                    │
                  │                                                │
                  │ ┌──────────────────────────┐                   │
                  │ │ iverilog                 │                   │
                  │ │                          │                   │
                  │ │ Compiles:                │                   │
                  │ │ 1) LLM-generated RTL     │ ◀──┐             │
                  │ │    (TopModule)           │    │             │
                  │ │ 2) Original RTL          │ ◀──┼──┐          │
                  │ │    (RefModule)           │    │  │          │
                  │ │ 3) Test bench            │ ◀──┘  │          │
                  │ └──────────────┬───────────┘       │          │
                  │                │                   │          │
                  │                ▼                   │          │
                  │ ┌──────────────────────────┐       │          │
                  │ │ ./Prob*_sample*          │       │          │
                  │ │ (Simulation binary)       │       │          │
                  │ │                          │       │          │
                  │ │ - Applies same inputs    │       │          │
                  │ │ - Compares outputs       │       │          │
                  │ │ - Counts mismatches      │       │          │
                  │ └──────────────┬───────────┘       │          │
                  │                │                   │          │
                  │                ▼                   │          │
                  │ ┌──────────────────────────┐       │          │
                  │ │ *-sv-iv-test.log         │       │          │
                  │ │ (Test results log)        │       │          │
                  │ └──────────────────────────┘       │          │
                  │                                    │          │
                  │                                    │          │
                  │ FILES USED:                        │          │
                  │                                    │          │
                  │ ┌──────────────────────────┐       │          │
                  │ │ Prob*_sample*.sv         │───────┘          │
                  │ │ (LLM-generated RTL)       │                  │
                  │ │                          │                  │
                  │ │ module TopModule(...);   │                  │
                  │ │   // LLM implementation  │                  │
                  │ │ endmodule                │                  │
                  │ └──────────────────────────┘                  │
                  │                                               │
                  │ ┌──────────────────────────┐                  │
                  │ │ Prob*_ref.sv             │──────────────────┘
                  │ │ (Original RTL)            │
                  │ │                          │
                  │ │ module RefModule(...);   │
                  │ │   // Reference impl      │
                  │ │ endmodule                │
                  │ └──────────────────────────┘
                  │
                  │ ┌──────────────────────────┐
                  │ │ Prob*_test.sv            │
                  │ │ (Test bench file)         │
                  │ │                          │
                  │ │ module tb();             │
                  │ │   // Instantiate both:   │
                  │ │   RefModule ref(...);    │
                  │ │   TopModule dut(...);    │
                  │ │                          │
                  │ │   // Compare outputs     │
                  │ │   // Report mismatches   │
                  │ │ endmodule                │
                  │ └──────────────────────────┘
                  │
                  └───────────────────────────┬───────────────────┘
                                             │
                                             ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           ANALYSIS (Step 5)                                    │
└───────────────────────────────────────────────────────────────────────────────┘
                                             │
┌────────────────────────────────────────────▼───────────────────────┐
│ make sv-iv-analyze                                                 │
└────────────────────────────────────────────┬───────────────────────┘
                                             │
                  ┌────────────────────────────────────────────────┐
                  │ scripts/sv-iv-analyze                          │
                  │                                                │
                  │ - Reads all test log files                     │
                  │ - Analyzes pass/fail status                    │
                  │ - Categorizes errors                           │
                  │ - Computes statistics                          │
                  └────────────────────────┬─────────────────────┘
                                           │
                                ┌──────────▼───────────┐
                                │                      │
                      ┌─────────▼──────────┐ ┌─────────▼──────────┐
                      │ summary.txt        │ │ summary.csv        │
                      │                    │ │                    │
                      │ Human-readable     │ │ Machine-readable   │
                      │ summary report     │ │ statistics        │
                      └────────────────────┘ └────────────────────┘
```

## Key Components

1. **Dataset Creation Process**: How the original RTL is synthesized to netlists
2. **Configuration Process**: How configure.ac sets up the build system
3. **RTL Generation**: How `make sv-generate` uses the LLM to generate RTL from netlists
4. **Testing Process**: How `make sv-iv-test` compiles and tests the generated RTL
5. **Analysis**: How `make sv-iv-analyze` processes test results

## Important Files and Their Roles

### Dataset Files
- **Prob*_ref.sv**: Original RTL reference implementation (module name: RefModule)
- **Prob*_netlist.v**: Synthesized gate-level netlist (module name: RefModule)
- **Prob*_test.sv**: Test bench that compares implementations
- **Prob*_prompt.txt**: Prompt for the LLM with netlist included

### Generated Files
- **Prob*_sample*.sv**: LLM-generated RTL (module name: TopModule)
- **Prob*_sample*-sv-generate.log**: Generation log
- **Prob*_sample*-sv-iv-test.log**: Testing results log

### Build System Files
- **configure.ac**: Configuration template
- **Makefile.in**: Makefile template
- **problems.mk**: Generated list of problems
- **samples.mk**: Generated number of samples per problem

## Workflow Steps

1. **ONE-TIME SETUP**: Generate netlist dataset from original RTL
2. **CONFIGURATION**: Set up build system for netlist-to-rtl task
3. **RTL GENERATION**: Generate RTL from netlists using LLM
4. **TESTING**: Compile and test LLM-generated RTL against reference
5. **ANALYSIS**: Analyze test results and generate statistics