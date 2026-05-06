# Automated Skill Discovery for Language Agents through Exploration and Iterative Feedback

Authors: Yongjin Yang, Sinjae Kang, Juyong Lee, Dongjun Lee, Se-young Yun, Kimin Lee
Year: 2025
Venue: arXiv.org
DOI: 10.48550/arXiv.2506.04287
URL: https://www.semanticscholar.org/paper/07f67a1187ad0bcd3dfa0f1e414b99ab9ca2ca17

## Abstract

Training large language model (LLM) agents to acquire necessary skills and perform diverse tasks within an environment is gaining interest as a means to enable open-endedness. However, creating the training dataset for their skill acquisition faces several challenges. Manual trajectory collection requires significant human effort. Another approach, where LLMs directly propose tasks to learn, is often invalid, as the LLMs lack knowledge of which tasks are actually feasible. Moreover, the generated data may not provide a meaningful learning signal, as agents often already perform well on the proposed tasks. To address this, we propose a novel automatic skill discovery framework EXIF for LLM-powered agents, designed to improve the feasibility of generated target behaviors while accounting for the agents'capabilities. Our method adopts an exploration-first strategy by employing an exploration agent (Alice) to train the target agent (Bob) to learn essential skills in the environment. Specifically, Alice first interacts with the environment to retrospectively generate a feasible, environment-grounded skill dataset, which is then used to train Bob. Crucially, we incorporate an iterative feedback loop, where Alice evaluates Bob's performance to identify areas for improvement. This feedback then guides Alice's next round of exploration, forming a closed-loop data generation process. Experiments on Webshop and Crafter demonstrate EXIF's ability to effectively discover meaningful skills and iteratively expand the capabilities of the trained agent without any human intervention, achieving substantial performance improvements. Interestingly, we observe that setting Alice to the same model as Bob also notably improves performance, demonstrating EXIF's potential for building a self-evolving system.

## Evidence

- Training large language model (LLM) agents to acquire necessary skills and perform diverse tasks within an environment is gaining interest as a means to enable open-endedness. However, creating the training dataset for their skill acquisition faces several challenges. Manual trajectory collection requires significant human effort. Another approach, where LLMs directly propose tasks to learn, is often invalid, as the LLMs lack knowledge of which tasks are actually feasible. Moreover, the generate
