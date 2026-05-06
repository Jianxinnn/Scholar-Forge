# Active Zero: Self-Evolving Vision-Language Models through Active Environment Exploration

Authors: Jinghan He, Junfeng Fang, Feng Xiong, Zijun Yao, Fei Shen, Haiyun Guo, Jinqiao Wang, Tat-Seng Chua
Year: 2026
Venue: arXiv.org
DOI: 10.48550/arXiv.2602.11241
URL: https://www.semanticscholar.org/paper/4ff7b902a44a3f02076baa73396adeb31f7eadd7

## Abstract

Self-play has enabled large language models to autonomously improve through self-generated challenges. However, existing self-play methods for vision-language models rely on passive interaction with static image collections, resulting in strong dependence on initial datasets and inefficient learning. Without the ability to actively seek visual data tailored to their evolving capabilities, agents waste computational effort on samples that are either trivial or beyond their current skill level. To address these limitations, we propose Active-Zero, a framework that shifts from passive interaction to active exploration of visual environments. Active-Zero employs three co-evolving agents: a Searcher that retrieves images from open-world repositories based on the model's capability frontier, a Questioner that synthesizes calibrated reasoning tasks, and a Solver refined through accuracy rewards. This closed loop enables self-scaffolding auto-curricula where the model autonomously constructs its learning trajectory. On Qwen2.5-VL-7B-Instruct across 12 benchmarks, Active-Zero achieves 53.97 average accuracy on reasoning tasks (5.7% improvement) and 59.77 on general understanding (3.9% improvement), consistently outperforming existing self-play baselines. These results highlight active exploration as a key ingredient for scalable and adaptive self-evolving vision-language systems.

## Evidence

- Self-play has enabled large language models to autonomously improve through self-generated challenges. However, existing self-play methods for vision-language models rely on passive interaction with static image collections, resulting in strong dependence on initial datasets and inefficient learning. Without the ability to actively seek visual data tailored to their evolving capabilities, agents waste computational effort on samples that are either trivial or beyond their current skill level. To
