# Gate-Breaker

Evaluation of LLMs on netlist-to-RTL recovery: the model is given a synthesized
gate-level netlist and has to produce RTL that passes the original testbench.
Generated RTL is scored by functional pass rate and by AST and CFG similarity
to the reference design.

This repository holds the analysis scripts and results. The benchmark harness
and the similarity tool live in two forks, included here as submodules.

| Submodule | Fork of | Upstream commit the fork is based on |
|---|---|---|
| `verilog-eval/` | https://github.com/NVlabs/verilog-eval | `c498220d0a52248f8e3fdffe279075215bde2da6` |
| `simeval/` | https://github.com/mhakyash/simeval | `d825354b36a319796ad3bd28a72efef0b2b66adc` |

## Layout

```
verilog-eval/   fork with the netlist-to-rtl task, dataset, prompts and experiment driver
simeval/        fork with improved_similarity_analysis.py
analysis/       scripts that turn run directories into metrics and tables
results/        metrics, similarity scores and tables from the completed runs
docs/           workflow description
```

## Getting the code

```
git clone --recurse-submodules <url of this repository>
```

In an existing clone, run `git submodule update --init`.

## Running experiments

Experiments run inside the `verilog-eval` submodule. Its README lists what the
fork adds and which tools the harness needs.

```
cd verilog-eval
./create_quartile_experiments.sh -h
./create_quartile_experiments.sh -m gpt4.1-mini -p cot -q q1 -r 1
```

Each run goes into `verilog-eval/<quartile>_<model>_<prompt>_shot2_run<N>/`.
API keys are read from the environment by the LLM client libraries. None are
stored in these repositories.

## Analysis

The scripts in `analysis/` read run directories from `verilog-eval/` and write
to `results/`. Set `GATE_BREAKER_RUNS` to read run directories from another
location.

| Script | Reads | Writes |
|---|---|---|
| `extract_all_metrics.py` | run directories | `results/all_experiment_metrics.csv` |
| `problem_level_frequency_analysis_fixed.py` | run directories | `results/problem_level_frequency_analysis_corrected.csv` |
| `run_similarity_analysis_loop.py` | run directories | `results/similarity_results/` |

`run_similarity_analysis_loop.py` expects a conda environment named `simeval`
and calls `simeval/improved_similarity_analysis.py`.

The raw run directories are not included. `results/results_summary/` has the
per-run summary text for each model.

## Citation

```bibtex
@inproceedings{faruque2025gate,
  title={Gate-Breaker: An LLM-Powered Netlist-to-RTL Reverse Engineering Tool},
  author={Faruque, Md Omar and Jamieson, Peter and Patooghy, Ahmad and Badawy, Abdel-Hameed A},
  booktitle={2025 IEEE International Performance, Computing, and Communications Conference (IPCCC)},
  pages={1--8},
  year={2025},
  organization={IEEE}
}
```

## License

MIT, see [LICENSE](LICENSE). The `verilog-eval` and `simeval` submodules are
separate repositories and keep their own terms.
