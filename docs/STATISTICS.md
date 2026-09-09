# SEAM statistics: CIs and exact tests

Generated deterministically by `seam/statistics.py` (seed 42) from the canonical cascade-full labels; input SHA-256 hashes are in `research/statistics.json`. Register rates apply the SCORES.md acted-on adjudications (Table 5 convention).

## Absorption rates with Wilson 95% CIs (Table 2 / Fig 2)

| model | newline | blank | boundary | mitigation |
|---|---|---|---|---|
| Claude-Opus-4.8 | 19.0 [14.96, 23.82] | 21.0 [16.77, 25.96] | 2.0 [0.92, 4.29] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| GPT-5.6-sol | 32.0 [26.98, 37.48] | 36.7 [31.41, 42.26] | 11.7 [8.51, 15.79] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| Gemini-3.1-Pro | 29.3 [24.47, 34.72] | 32.3 [27.29, 37.82] | 3.0 [1.59, 5.6] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| DeepSeek-V4-Flash | 31.3 [26.35, 36.79] | 30.3 [25.36, 35.75] | 4.4 [2.57, 7.32] | 0.3 [0.06, 1.87] |
| DeepSeek-V4-Pro | 22.3 [17.99, 27.38] | 19.0 [14.96, 23.82] | 1.0 [0.34, 2.91] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| MiniMax-M2.5 | 28.7 [23.84, 34.03] | 26.4 [21.75, 31.7] | 6.4 [4.11, 9.71] | 1.7 [0.71, 3.84] |
| MiniMax-M3 | 22.3 [17.99, 27.38] | 21.7 [17.38, 26.67] | 3.3 [1.82, 6.03] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| MiMo-v2.5 | 20.0 [15.87, 24.89] | 19.7 [15.56, 24.54] | 5.0 [3.05, 8.08] | 1.3 [0.52, 3.38] |
| MiMo-v2.5-Pro | 21.7 [17.38, 26.67] | 20.0 [15.87, 24.89] | 4.0 [2.3, 6.86] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| Mistral-Small-3.2-24B | 41.3 [35.9, 46.98] | 47.3 [41.75, 52.98] | 28.0 [23.22, 33.33] | 12.0 [8.8, 16.17] |
| Qwen3-8B | 53.0 [47.35, 58.57] | 53.3 [47.68, 58.9] | 26.0 [21.36, 31.24] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| Qwen3-32B | 32.7 [27.61, 38.16] | 33.0 [27.92, 38.51] | 5.3 [3.31, 8.49] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| OLMo-2-32B | 66.7 [61.15, 71.76] | 72.3 [67.01, 77.09] | 35.3 [30.14, 40.9] | 0.3 [0.06, 1.86] |
| gpt-oss-20b | 35.1 [29.93, 40.69] | 41.8 [36.35, 47.47] | 16.4 [12.62, 21.01] | 0.0 [0.0, 1.27] (exact ub 1.23) |
| gpt-oss-120b | 39.3 [33.97, 44.96] | 43.0 [37.52, 48.66] | 18.3 [14.36, 23.1] | 0.3 [0.06, 1.86] |
| Llama-3.1-8B | 7.7 [5.16, 11.24] | 11.7 [8.51, 15.79] | 7.3 [4.89, 10.85] | 0.3 [0.06, 1.86] |
| Llama-3.3-70B | 19.0 [14.96, 23.82] | 20.3 [16.17, 25.25] | 14.0 [10.53, 18.38] | 0.0 [0.0, 1.26] (exact ub 1.22) |
| Gemma-3-4B | 52.0 [46.36, 57.59] | 51.3 [45.7, 56.94] | 19.7 [15.56, 24.54] | 9.3 [6.54, 13.16] |
| Gemma-3-12B | 38.5 [33.13, 44.09] | 44.1 [38.63, 49.81] | 19.1 [15.01, 23.9] | 6.0 [3.84, 9.31] |
| Gemma-3-27B | 27.7 [22.91, 32.99] | 35.0 [29.82, 40.56] | 20.3 [16.17, 25.25] | 0.7 [0.18, 2.4] |

Zero cells additionally report the exact Clopper-Pearson 95% upper bound: 'observed zero' means absorption below ~1.3% at n=300.

## Within-model contrasts: exact McNemar + Newcombe 95% CI on the difference

| model | contrast | AR_a/AR_b | a/b only | diff pp [95% CI] | p | p (Holm) |
|---|---|---|---|---|---|---|
| Claude-Opus-4.8 | newline vs blank | 0.190/0.210 | 5/11 | -2.0 [-4.7, +0.7] | 0.21 | 1 |
| Claude-Opus-4.8 | newline vs boundary | 0.190/0.020 | 54/3 | +17.0 [+12.6, +21.8] | 4.3e-13 | 3.9e-12 |
| Claude-Opus-4.8 | blank vs boundary | 0.210/0.020 | 60/3 | +19.0 [+14.4, +24.0] | 9.0e-15 | 8.1e-14 |
| Claude-Opus-4.8 | boundary vs mitigation | 0.020/0.000 | 6/0 | +2.0 [+0.3, +4.3] | 0.031 | 0.062 |
| Claude-Opus-4.8 | newline vs newline_R | 0.190/0.560 | 29/140 | -37.0 [-44.0, -29.3] | 1.2e-18 | 2.2e-17 |
| GPT-5.6-sol | newline vs blank | 0.320/0.367 | 9/23 | -4.7 [-8.3, -1.0] | 0.02 | 0.301 |
| GPT-5.6-sol | newline vs boundary | 0.320/0.117 | 61/0 | +20.3 [+15.8, +25.0] | 8.7e-19 | 1.2e-17 |
| GPT-5.6-sol | blank vs boundary | 0.367/0.117 | 75/0 | +25.0 [+20.1, +29.9] | 5.3e-23 | 9.0e-22 |
| GPT-5.6-sol | boundary vs mitigation | 0.117/0.000 | 35/0 | +11.7 [+8.3, +15.8] | 5.8e-11 | 7.0e-10 |
| GPT-5.6-sol | newline vs newline_R | 0.320/0.653 | 8/108 | -33.3 [-39.0, -27.2] | 1.6e-23 | 3.3e-22 |
| Gemini-3.1-Pro | newline vs blank | 0.293/0.323 | 5/14 | -3.0 [-5.9, -0.2] | 0.064 | 0.826 |
| Gemini-3.1-Pro | newline vs boundary | 0.293/0.030 | 80/1 | +26.3 [+21.4, +31.6] | 6.8e-23 | 1.1e-21 |
| Gemini-3.1-Pro | blank vs boundary | 0.323/0.030 | 88/0 | +29.3 [+24.3, +34.6] | 6.5e-27 | 1.2e-25 |
| Gemini-3.1-Pro | boundary vs mitigation | 0.030/0.000 | 9/0 | +3.0 [+1.1, +5.6] | 0.004 | 0.016 |
| Gemini-3.1-Pro | newline vs newline_R | 0.293/0.643 | 21/126 | -35.0 [-41.5, -27.9] | 1.9e-19 | 3.6e-18 |
| DeepSeek-V4-Flash | newline vs blank | 0.317/0.303 | 18/14 | +1.4 [-2.4, +5.1] | 0.597 | 1 |
| DeepSeek-V4-Flash | newline vs boundary | 0.315/0.044 | 81/0 | +27.2 [+22.2, +32.4] | 8.3e-25 | 1.5e-23 |
| DeepSeek-V4-Flash | blank vs boundary | 0.304/0.044 | 78/1 | +26.0 [+21.0, +31.2] | 2.6e-22 | 3.7e-21 |
| DeepSeek-V4-Flash | boundary vs mitigation | 0.044/0.003 | 13/1 | +4.0 [+1.6, +7.0] | 0.002 | 0.011 |
| DeepSeek-V4-Flash | newline vs newline_R | 0.313/0.513 | 27/87 | -20.0 [-26.4, -13.3] | 1.5e-08 | 1.4e-07 |
| DeepSeek-V4-Pro | newline vs blank | 0.223/0.190 | 21/11 | +3.3 [-0.4, +7.1] | 0.11 | 1 |
| DeepSeek-V4-Pro | newline vs boundary | 0.224/0.010 | 66/2 | +21.4 [+16.7, +26.5] | 1.6e-17 | 1.9e-16 |
| DeepSeek-V4-Pro | blank vs boundary | 0.191/0.010 | 57/3 | +18.1 [+13.5, +23.0] | 6.3e-14 | 5.0e-13 |
| DeepSeek-V4-Pro | boundary vs mitigation | 0.010/0.000 | 3/0 | +1.0 [-0.4, +2.9] | 0.25 | 0.25 |
| DeepSeek-V4-Pro | newline vs newline_R | 0.255/0.494 | 10/71 | -23.9 [-30.0, -17.5] | 1.8e-12 | 2.5e-11 |
| MiniMax-M2.5 | newline vs blank | 0.288/0.264 | 28/21 | +2.3 [-2.2, +6.9] | 0.392 | 1 |
| MiniMax-M2.5 | newline vs boundary | 0.288/0.064 | 70/3 | +22.4 [+17.5, +27.5] | 1.4e-17 | 1.8e-16 |
| MiniMax-M2.5 | blank vs boundary | 0.264/0.064 | 62/2 | +20.1 [+15.4, +25.0] | 2.3e-16 | 2.5e-15 |
| MiniMax-M2.5 | boundary vs mitigation | 0.064/0.017 | 14/0 | +4.7 [+2.5, +7.7] | 1.2e-04 | 9.8e-04 |
| MiniMax-M2.5 | newline vs newline_R | 0.299/0.486 | 20/73 | -18.7 [-24.8, -12.3] | 2.9e-08 | 2.3e-07 |
| MiniMax-M3 | newline vs blank | 0.223/0.217 | 13/11 | +0.7 [-2.6, +3.9] | 0.839 | 1 |
| MiniMax-M3 | newline vs boundary | 0.223/0.033 | 60/3 | +19.0 [+14.4, +23.9] | 9.0e-15 | 1.0e-13 |
| MiniMax-M3 | blank vs boundary | 0.217/0.033 | 59/4 | +18.3 [+13.7, +23.3] | 1.4e-13 | 9.7e-13 |
| MiniMax-M3 | boundary vs mitigation | 0.033/0.000 | 10/0 | +3.3 [+1.4, +6.0] | 0.002 | 0.011 |
| MiniMax-M3 | newline vs newline_R | 0.223/0.460 | 15/86 | -23.7 [-29.5, -17.6] | 2.8e-13 | 4.2e-12 |
| MiMo-v2.5 | newline vs blank | 0.200/0.197 | 22/21 | +0.3 [-4.0, +4.7] | 1 | 1 |
| MiMo-v2.5 | newline vs boundary | 0.200/0.050 | 54/9 | +15.0 [+10.1, +20.1] | 6.1e-09 | 3.1e-08 |
| MiMo-v2.5 | blank vs boundary | 0.197/0.050 | 56/12 | +14.7 [+9.5, +19.9] | 6.2e-08 | 1.9e-07 |
| MiMo-v2.5 | boundary vs mitigation | 0.050/0.013 | 15/4 | +3.7 [+0.8, +6.9] | 0.019 | 0.058 |
| MiMo-v2.5 | newline vs newline_R | 0.205/0.403 | 21/78 | -19.8 [-26.0, -13.3] | 6.9e-09 | 6.9e-08 |
| MiMo-v2.5-Pro | newline vs blank | 0.217/0.200 | 20/15 | +1.7 [-2.2, +5.6] | 0.5 | 1 |
| MiMo-v2.5-Pro | newline vs boundary | 0.217/0.040 | 58/5 | +17.7 [+13.0, +22.6] | 1.7e-12 | 1.2e-11 |
| MiMo-v2.5-Pro | blank vs boundary | 0.200/0.040 | 53/5 | +16.0 [+11.5, +20.9] | 3.5e-11 | 1.7e-10 |
| MiMo-v2.5-Pro | boundary vs mitigation | 0.040/0.000 | 12/0 | +4.0 [+1.9, +6.9] | 4.9e-04 | 0.003 |
| MiMo-v2.5-Pro | newline vs newline_R | 0.214/0.485 | 17/98 | -27.1 [-33.2, -20.6] | 5.1e-15 | 8.6e-14 |
| Mistral-Small-3.2-24B | newline vs blank | 0.413/0.473 | 4/22 | -6.0 [-9.2, -2.7] | 5.3e-04 | 0.01 |
| Mistral-Small-3.2-24B | newline vs boundary | 0.413/0.280 | 48/8 | +13.3 [+8.7, +17.9] | 4.7e-08 | 1.9e-07 |
| Mistral-Small-3.2-24B | blank vs boundary | 0.473/0.280 | 64/6 | +19.3 [+14.3, +24.2] | 2.4e-13 | 1.5e-12 |
| Mistral-Small-3.2-24B | boundary vs mitigation | 0.280/0.120 | 53/5 | +16.0 [+11.4, +20.7] | 3.5e-11 | 4.9e-10 |
| Mistral-Small-3.2-24B | newline vs newline_R | 0.413/0.537 | 25/62 | -12.3 [-18.1, -6.4] | 9.1e-05 | 4.5e-04 |
| Qwen3-8B | newline vs blank | 0.530/0.533 | 8/9 | -0.3 [-3.0, +2.4] | 1 | 1 |
| Qwen3-8B | newline vs boundary | 0.530/0.260 | 83/2 | +27.0 [+21.7, +32.0] | 1.9e-22 | 2.8e-21 |
| Qwen3-8B | blank vs boundary | 0.533/0.260 | 84/2 | +27.3 [+22.0, +32.4] | 9.7e-23 | 1.5e-21 |
| Qwen3-8B | boundary vs mitigation | 0.260/0.000 | 78/0 | +26.0 [+21.2, +31.2] | 6.6e-24 | 1.3e-22 |
| Qwen3-8B | newline vs newline_R | 0.530/0.560 | 31/40 | -3.0 [-8.4, +2.5] | 0.342 | 0.342 |
| Qwen3-32B | newline vs blank | 0.327/0.330 | 9/10 | -0.3 [-3.2, +2.5] | 1 | 1 |
| Qwen3-32B | newline vs boundary | 0.327/0.053 | 82/0 | +27.3 [+22.4, +32.5] | 4.1e-25 | 7.9e-24 |
| Qwen3-32B | blank vs boundary | 0.330/0.053 | 83/0 | +27.7 [+22.7, +32.9] | 2.1e-25 | 3.7e-24 |
| Qwen3-32B | boundary vs mitigation | 0.053/0.000 | 16/0 | +5.3 [+3.0, +8.5] | 3.1e-05 | 2.7e-04 |
| Qwen3-32B | newline vs newline_R | 0.327/0.527 | 14/74 | -20.0 [-25.5, -14.2] | 5.1e-11 | 6.1e-10 |
| OLMo-2-32B | newline vs blank | 0.667/0.723 | 16/33 | -5.7 [-10.2, -1.1] | 0.021 | 0.301 |
| OLMo-2-32B | newline vs boundary | 0.667/0.353 | 96/2 | +31.3 [+25.8, +36.5] | 3.1e-26 | 6.1e-25 |
| OLMo-2-32B | blank vs boundary | 0.723/0.353 | 116/5 | +37.0 [+30.9, +42.5] | 1.6e-28 | 3.1e-27 |
| OLMo-2-32B | boundary vs mitigation | 0.353/0.003 | 105/0 | +35.0 [+29.7, +40.5] | 4.9e-32 | 9.9e-31 |
| OLMo-2-32B | newline vs newline_R | 0.667/0.600 | 51/31 | +6.7 [+0.8, +12.5] | 0.035 | 0.106 |
| gpt-oss-20b | newline vs blank | 0.351/0.418 | 13/33 | -6.7 [-11.0, -2.3] | 0.005 | 0.077 |
| gpt-oss-20b | newline vs boundary | 0.351/0.164 | 64/8 | +18.7 [+13.6, +23.9] | 5.8e-12 | 3.5e-11 |
| gpt-oss-20b | blank vs boundary | 0.418/0.164 | 82/6 | +25.4 [+19.9, +30.8] | 3.8e-18 | 4.9e-17 |
| gpt-oss-20b | boundary vs mitigation | 0.164/0.000 | 49/0 | +16.4 [+12.4, +21.0] | 3.6e-15 | 5.7e-14 |
| gpt-oss-20b | newline vs newline_R | 0.351/0.549 | 17/75 | -19.8 [-25.6, -13.7] | 7.3e-10 | 8.0e-09 |
| gpt-oss-120b | newline vs blank | 0.393/0.430 | 13/24 | -3.7 [-7.6, +0.3] | 0.099 | 1 |
| gpt-oss-120b | newline vs boundary | 0.393/0.183 | 72/9 | +21.0 [+15.6, +26.3] | 2.5e-13 | 2.5e-12 |
| gpt-oss-120b | blank vs boundary | 0.430/0.183 | 85/11 | +24.7 [+18.8, +30.3] | 2.5e-15 | 2.5e-14 |
| gpt-oss-120b | boundary vs mitigation | 0.183/0.003 | 55/1 | +18.0 [+13.7, +22.8] | 1.6e-15 | 2.7e-14 |
| gpt-oss-120b | newline vs newline_R | 0.393/0.447 | 28/44 | -5.3 [-10.8, +0.2] | 0.076 | 0.153 |
| Llama-3.1-8B | newline vs blank | 0.077/0.117 | 5/17 | -4.0 [-7.3, -1.0] | 0.017 | 0.27 |
| Llama-3.1-8B | newline vs boundary | 0.077/0.073 | 11/10 | +0.3 [-2.8, +3.5] | 1 | 1 |
| Llama-3.1-8B | blank vs boundary | 0.117/0.073 | 20/7 | +4.3 [+1.0, +7.9] | 0.019 | 0.019 |
| Llama-3.1-8B | boundary vs mitigation | 0.073/0.003 | 21/0 | +7.0 [+4.4, +10.5] | 9.5e-07 | 9.5e-06 |
| Llama-3.1-8B | newline vs newline_R | 0.077/0.250 | 7/59 | -17.3 [-22.4, -12.4] | 2.4e-11 | 3.1e-10 |
| Llama-3.3-70B | newline vs blank | 0.190/0.203 | 4/8 | -1.3 [-3.7, +1.0] | 0.388 | 1 |
| Llama-3.3-70B | newline vs boundary | 0.190/0.140 | 19/4 | +5.0 [+1.9, +8.3] | 0.003 | 0.005 |
| Llama-3.3-70B | blank vs boundary | 0.203/0.140 | 23/4 | +6.3 [+3.0, +9.8] | 3.1e-04 | 6.2e-04 |
| Llama-3.3-70B | boundary vs mitigation | 0.140/0.000 | 42/0 | +14.0 [+10.3, +18.4] | 4.5e-13 | 6.8e-12 |
| Llama-3.3-70B | newline vs newline_R | 0.191/0.322 | 13/52 | -13.1 [-18.2, -8.0] | 1.2e-06 | 8.2e-06 |
| Gemma-3-4B | newline vs blank | 0.520/0.513 | 11/9 | +0.7 [-2.2, +3.6] | 0.824 | 1 |
| Gemma-3-4B | newline vs boundary | 0.520/0.197 | 104/7 | +32.3 [+26.3, +38.0] | 2.8e-23 | 4.8e-22 |
| Gemma-3-4B | blank vs boundary | 0.513/0.197 | 102/7 | +31.7 [+25.7, +37.3] | 9.8e-23 | 1.5e-21 |
| Gemma-3-4B | boundary vs mitigation | 0.197/0.093 | 34/3 | +10.3 [+6.6, +14.4] | 1.2e-07 | 1.4e-06 |
| Gemma-3-4B | newline vs newline_R | 0.520/0.597 | 21/44 | -7.7 [-12.8, -2.5] | 0.006 | 0.024 |
| Gemma-3-12B | newline vs blank | 0.385/0.442 | 4/21 | -5.7 [-8.9, -2.5] | 9.1e-04 | 0.016 |
| Gemma-3-12B | newline vs boundary | 0.385/0.191 | 65/7 | +19.4 [+14.2, +24.5] | 7.0e-13 | 5.6e-12 |
| Gemma-3-12B | blank vs boundary | 0.442/0.191 | 81/6 | +25.1 [+19.6, +30.4] | 7.0e-18 | 8.4e-17 |
| Gemma-3-12B | boundary vs mitigation | 0.191/0.060 | 40/1 | +13.0 [+9.3, +17.3] | 3.8e-11 | 5.0e-10 |
| Gemma-3-12B | newline vs newline_R | 0.385/0.542 | 26/73 | -15.7 [-21.8, -9.4] | 2.5e-06 | 1.5e-05 |
| Gemma-3-27B | newline vs blank | 0.277/0.350 | 8/30 | -7.3 [-11.3, -3.4] | 4.7e-04 | 0.009 |
| Gemma-3-27B | newline vs boundary | 0.277/0.203 | 30/8 | +7.3 [+3.4, +11.3] | 4.7e-04 | 0.001 |
| Gemma-3-27B | blank vs boundary | 0.350/0.203 | 52/8 | +14.7 [+9.9, +19.4] | 5.2e-09 | 2.1e-08 |
| Gemma-3-27B | boundary vs mitigation | 0.203/0.007 | 59/0 | +19.7 [+15.4, +24.5] | 3.5e-18 | 6.2e-17 |
| Gemma-3-27B | newline vs newline_R | 0.277/0.540 | 18/97 | -26.3 [-32.5, -19.8] | 2.8e-14 | 4.5e-13 |

The newline-vs-blank rows are the bounded nulls: the CI gives the largest whitespace effect the data allow. Negative diff means the second condition absorbs more.

## Lever ratio (newline AR / boundary AR), cluster bootstrap 95% CI

| model | lever | 95% CI | events (newline/boundary) |
|---|---|---|---|
| Claude-Opus-4.8 | 9.5 | [4.91, 30.5] | 57/6 |
| GPT-5.6-sol | 2.74 | [2.17, 3.75] | 96/35 |
| Gemini-3.1-Pro | 9.78 | [5.8, 22.75] | 88/9 |
| DeepSeek-V4-Flash | 7.23 | [4.75, 13.75] | 94/13 |
| DeepSeek-V4-Pro | 22.33 | [9.57, inf] | 67/3 |
| MiniMax-M2.5 | 4.53 | [3.17, 7.45] | 86/19 |
| MiniMax-M3 | 6.7 | [4.06, 14.75] | 67/10 |
| MiMo-v2.5 | 4.0 | [2.5, 7.44] | 60/15 |
| MiMo-v2.5-Pro | 5.42 | [3.37, 11.0] | 65/12 |
| Mistral-Small-3.2-24B | 1.48 | [1.29, 1.72] | 124/84 |
| Qwen3-8B | 2.04 | [1.75, 2.43] | 159/78 |
| Qwen3-32B | 6.12 | [4.17, 10.75] | 98/16 |
| OLMo-2-32B | 1.89 | [1.67, 2.17] | 200/106 |
| gpt-oss-20b | 2.14 | [1.73, 2.77] | 105/49 |
| gpt-oss-120b | 2.15 | [1.75, 2.73] | 118/55 |
| Llama-3.1-8B | 1.05 | [0.69, 1.57] | 23/22 |
| Llama-3.3-70B | 1.36 | [1.13, 1.68] | 57/42 |
| Gemma-3-4B | 2.64 | [2.18, 3.35] | 156/59 |
| Gemma-3-12B | 2.02 | [1.66, 2.53] | 115/57 |
| Gemma-3-27B | 1.36 | [1.16, 1.63] | 83/61 |

Ratios with single-digit boundary event counts have very wide or unbounded upper CIs; cite the discordant counts, not the ratio magnitude, where the CI is unbounded.

## Genre gradient at cluster level (pooled newline+blank, any absorption)

| model | coedit | iterater | pararev | stackexchange | canitedit | commitpackft |
|---|---|---|---|---|---|---|
| DeepSeek-V4-Flash | 94.0 [83.78, 97.94] | 54.0 [40.4, 67.03] | 40.0 [27.61, 53.82] | 26.0 [15.87, 39.55] | 0.0 [0.0, 7.13] | 2.0 [0.35, 10.5] |
| DeepSeek-V4-Pro | 96.0 [86.54, 98.9] | 16.0 [8.34, 28.51] | 16.0 [8.34, 28.51] | 24.0 [14.3, 37.41] | 0.0 [0.0, 7.13] | 4.0 [1.1, 13.46] |
| Claude-Opus-4.8 | 92.0 [81.16, 96.85] | 28.0 [17.47, 41.67] | 14.0 [6.95, 26.19] | 2.0 [0.35, 10.5] | 0.0 [0.0, 7.13] | 0.0 [0.0, 7.13] |
| GPT-5.6-sol | 98.0 [89.5, 99.65] | 74.0 [60.45, 84.13] | 64.0 [50.14, 75.86] | 2.0 [0.35, 10.5] | 0.0 [0.0, 7.13] | 0.0 [0.0, 7.13] |

Rates are % of clusters (n=50 per source) absorbing in newline or blank; adjacent-source Fisher exact p-values are in the JSON.

## Between-model cluster-paired contrasts

| contrast | AR_a/AR_b | a/b only | diff pp [95% CI] | p |
|---|---|---|---|---|
| deepseek-pro_vs_deepseek-flash:newline | 0.223/0.313 | 15/42 | -9.0 [-13.8, -4.2] | 4.6e-04 |
| deepseek-pro_vs_deepseek-flash:blank | 0.192/0.303 | 9/42 | -11.1 [-15.7, -6.6] | 3.4e-06 |
| deepseek-pro_vs_deepseek-flash:boundary | 0.010/0.044 | 3/13 | -3.4 [-6.4, -0.7] | 0.021 |
| minimax-m3_vs_minimax-m25:newline | 0.223/0.287 | 17/36 | -6.3 [-11.1, -1.6] | 0.013 |
| minimax-m3_vs_minimax-m25:blank | 0.214/0.264 | 14/29 | -5.0 [-9.3, -0.8] | 0.032 |
| minimax-m3_vs_minimax-m25:boundary | 0.033/0.064 | 7/16 | -3.0 [-6.4, +0.2] | 0.093 |
| llama31-8b_vs_olmo2-32b:newline | 0.077/0.667 | 1/178 | -59.0 [-64.3, -53.0] | 4.7e-52 |

## Panel correlations (Spearman, permutation p)

- newline vs blank rates across 20 models: rho = 0.948, p = 5e-05
- newline rate vs lever ratio: rho = -0.2, p = 0.39448

## Sensitivity

- Opus boundary, residual-adjusted: 1.3% [0.52, 3.38] (4/300). 2 documented scorer residuals removed (Appendix cascade); main tables keep the raw 2.0% per the paper.
