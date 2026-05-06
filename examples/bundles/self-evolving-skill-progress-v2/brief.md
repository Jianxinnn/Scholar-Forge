# Research Brief

## 一句话结论
2024–2026 年“自进化（self-evolving）”智能体技能（skill）研究正从“基于提示词的临时工具调用”转向“可移植、可验证、可持续迭代的技能库/技能层”，并开始引入强化学习、持续学习基准、双环架构与形式化约束以支撑长期自我改进与安全性保证 [src_ed048773e5455f29657c, src_d46417433c61e2a91be6, src_1ec6b2611f09bb621f1e]。

## 主要研究路线
1) **技能层（Skill Layer）与模块化封装**：将可复用过程能力封装为“技能模块”，包含适用条件、执行策略、终止条件与接口，以区别于一次性计划/单步工具调用，并覆盖从发现、练习、蒸馏、存储、组合到更新的全生命周期 [src_d46417433c61e2a91be6]。面向实践部署，强调“可移植技能定义、渐进式披露（progressive disclosure）、与 MCP 集成”的技能化范式 [src_b049c483370951c9969c]。  
2) **从经验到技能的自进化闭环**：围绕“生成—验证—执行—失败归因—再生成/再精炼”的闭环，让技能库随运行经验增长并纠错，面向 Web、企业支持、科学研究等场景 [src_c7d5a5097a669e7f906b, src_7ada95852adce570d6a1, src_2e891cf55708d0a8f5cd]。  
3) **学习驱动的自我改进（RL/符号/带宽分配）**：用学习机制替代纯提示词工程，使技能选择、检索策略、以及技能库更新更稳定可控。例如用 RL 强化技能库自我改进 [src_ed048773e5455f29657c]，用两时间尺度框架学习检索策略与慢速自适应 [src_6f23fd6a05711297118d]，以及强调从“工程/模型中心”转向“从数据自动学习”的立场 [src_4c68efd8a0e8767ee6cb]。  
4) **记忆能力技能化**：将记忆提取、整合、剪枝等操作从静态规则重构为可学习、可演化的“记忆技能”，并通过控制器选择相关技能以适配长历史与多样交互模式 [src_78741fb5f920631a11d9]。  
5) **评测与持续学习基准化**：构建针对“持续技能学习/技能生成”的基准，从技能质量、执行轨迹、任务结果等多层面评估不同持续学习技术与反馈机制 [src_efe104582336a2c2377c]。  
6) **领域化自进化与工具编排**：在 OS 级计算机代理、医学影像、心理咨询、RTL 优化、科研工作流等领域，突出“工具密集、长时程、失败可追踪”的自改进需求，常以层级规划/执行、经验驱动技能发现与持续优化为核心 [src_e761b6bcbbcfcab51cdf, src_b898768094bd6fa531b5, src_a14d3ec9d9267d261539, src_61c50dd71b5dab8c226f, src_424a6bcfe43138e4c93c]。  
7) **可验证/受约束的自进化**：针对自进化代理缺乏安全与正确性保证的问题，将“生成可执行代理程序”表述为带硬约束（形式化规格）与软目标（效用）的受约束学习问题，以提升自治执行的可靠性 [src_1ec6b2611f09bb621f1e]。

## 前沿代表工作
- **SAGE（Skill Augmented GRPO for self-Evolution）**：提出 RL 驱动的技能库自我改进思路，旨在缓解仅靠 LLM prompting 导致的一致性与落地困难 [src_ed048773e5455f29657c]。  
- **SkillWeaver（Web 代理自我发现与打磨技能）**：面向网站环境，强调从探索与执行中抽象出可复用技能（以 API 形式）并通过练习与组合提升能力 [src_c7d5a5097a669e7f906b]。  
- **SkillFoundry（异构科研资源→可验证技能）**：将脚本、API、文档、notebook、论文等异构资源转化为带范围、I/O、环境假设、溯源与测试的“验证型技能”，以缓解科学知识碎片化与不可操作化问题 [src_2e891cf55708d0a8f5cd]。  
- **SkillForge（企业云技术支持的端到端闭环）**：用领域上下文约束技能合成，并将执行失败追溯到技能缺陷以驱动定向精炼，解决“部署后技能质量停滞”的问题 [src_7ada95852adce570d6a1]。  
- **MemSkill（记忆操作技能化与可演化）**：把记忆抽取/巩固/剪枝流程视为可学习技能，由控制器选择少量相关技能应对长历史与交互多样性 [src_78741fb5f920631a11d9]。  
- **AEL（两时间尺度的演化学习）**：指出开放式多回合环境中关键障碍在于“如何使用已记忆内容”，并用快尺度 bandit 学检索策略、慢尺度自适应来支撑跨 episode 改进 [src_6f23fd6a05711297118d]。  
- **SEVerA（可验证的自进化代理综合）**：针对自进化框架缺少形式保证，提出将代理代码生成纳入带硬规格约束与软目标的学习框架，强调安全/正确性 [src_1ec6b2611f09bb621f1e]。  
- **S1-NexusAgent（科研自进化框架）**：用层级 Plan-and-CodeAct 与双环结构解耦全局规划与子任务工具执行，以稳定建模复杂科研工作流并支持持续学习 [src_424a6bcfe43138e4c93c]。  
- **OS-Copilot（通用计算机代理与自改进）**：面向操作系统级多工具（网页、终端、文件、多媒体、第三方应用）交互，强调通用性与自我改进需求 [src_e761b6bcbbcfcab51cdf]。  
- **领域自进化案例（医学影像/咨询/RTL）**：从“静态工具链脆弱”出发，转向经验增强与持续优化的自进化设计，体现强工具依赖与高风险场景下的迭代压力 [src_b898768094bd6fa531b5, src_a14d3ec9d9267d261539, src_61c50dd71b5dab8c226f]。  
- **SkillLearnBench（持续技能学习评测）**：提出面向真实任务的持续技能生成/学习基准，并从技能质量、执行轨迹、任务结果三层评估方法有效性 [src_efe104582336a2c2377c]。  
- **技能综述与系统化（Agent Skills / SoK Agentic Skills）**：总结技能化部署从架构、获取到安全的关键问题，并给出技能生命周期与设计模式/分类学，以指导系统设计与审计 [src_b049c483370951c9969c, src_d46417433c61e2a91be6]。

## 对自进化 Skill 系统的设计启示
1) **把“技能”定义为可审计对象**：技能应包含清晰的适用条件、接口、执行/终止策略与可复用边界，支持生命周期管理（发现→练习→蒸馏→存储→组合→更新）以便审计追踪与回滚 [src_d46417433c61e2a91be6]。  
2) **构建端到端闭环而非一次性生成**：将线上失败与日志转化为“技能缺陷信号”，驱动定向再生成/再精炼，形成持续改进流水线 [src_7ada95852adce570d6a1, src_c7d5a5097a669e7f906b]。  
3) **技能库建设要“资源可转译 + 可验证”**：从异构资源自动提取过程知识时，应同时产出溯源与测试/验证物料，降低碎片知识不可执行的风险 [src_2e891cf55708d0a8f5cd]。  
4) **用学习机制稳定“选择/检索/更新”策略**：在技能选择与自改进上引入 RL 或分层学习（如两时间尺度），减少纯提示工程的不确定性，并支撑跨 episode 的性能累积 [src_ed048773e5455f29657c, src_6f23fd6a05711297118d]。  
5) **将记忆也技能化**：把“存什么、怎么改、何时剪枝”从固定规则变为可学习技能，并用控制器在交互轨迹上动态选择，提升长程一致性与效率 [src_78741fb5f920631a11d9]。  
6) **采用层级/双环架构解耦规划与执行**：将全局目标维护与子任务工具执行分离，提升长时程任务的稳定性与可诊断性 [src_424a6bcfe43138e4c93c]。  
7) **将“安全与正确性”纳入自进化接口**：对自生成代理程序/技能更新引入硬性规格约束与验证思路，降低自治执行在未知输入上的失控风险 [src_1ec6b2611f09bb621f1e]。

## 风险与缺口
1) **缺少形式保证导致的可靠性与安全风险**：自进化框架若缺少安全/正确性约束，自治执行在未见输入上可能带来可靠性与安全隐患 [src_1ec6b2611f09bb621f1e]。  
2) **提示词主导的技能库一致性问题**：仅依赖 LLM prompting 的技能库实现可能难以保持一致、可重复与可维护，从而限制持续自改进 [src_ed048773e5455f29657c]。  
3) **开放式多回合环境的“会记但不会用”**：关键挑战不只是记忆存储，而在于检索策略选择、对过往结果的解释以及何时改变策略 [src_6f23fd6a05711297118d]。  
4) **静态工具链在真实分布漂移下脆弱**：将工具集与调用策略视为部署后静态配置会在跨任务/域移中退化，迫使人工重设计 [src_b898768094bd6fa531b5]。  
5) **评测不足与可比性问题**：持续技能学习方法需要更系统的基准来衡量技能质量、执行过程与最终结果，否则难以审计不同自进化策略的收益与代价 [src_efe104582336a2c2377c]。

## 建议下一步
1) **建立“技能变更审计链”**：对每次技能新增/更新记录触发原因（失败类型/指标）、溯源证据、回归测试结果与影响面，按技能生命周期管理以支持回滚与责任界定 [src_d46417433c61e2a91be6, src_7ada95852adce570d6a1]。  
2) **引入可验证更新门禁（gating）**：对自进化产生的代理程序/技能更新，采用硬规格约束 + 软目标优化的受约束生成/学习门禁，优先覆盖高风险工具与关键技能 [src_1ec6b2611f09bb621f1e]。  
3) **用基准驱动持续学习迭代**：以持续技能学习基准对“技能质量/轨迹/结果”三层指标做 A/B，对不同反馈机制（自反馈/教师反馈/技能创建器）做可比评测 [src_efe104582336a2c2377c]。  
4) **把“记忆策略”纳入技能库统一治理**：将记忆操作作为技能，与任务技能共享版本、评测与更新策略，并为检索策略引入学习机制以避免长期漂移 [src_78741fb5f920631a11d9, src_6f23fd6a05711297118d]。  
5) **优先落地“资源→技能→测试”的转译流水线**：从文档/脚本/API 等异构资源自动构建带测试的技能资产，减少纯自然语言技能的不可执行与不可验证问题 [src_2e891cf55708d0a8f5cd]。  

## Key Sources
- [src_ed048773e5455f29657c] Reinforcement Learning for Self-Improving Agent with Skill Library (2025)  
- [src_d46417433c61e2a91be6] SoK: Agentic Skills - Beyond Tool Use in LLM Agents (2026)  
- [src_b049c483370951c9969c] Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward (2026)  
- [src_c7d5a5097a669e7f906b] SkillWeaver: Web Agents can Self-Improve by Discovering and Honing Skills (2025)  
- [src_2e891cf55708d0a8f5cd] SKILLFOUNDRY: Building Self-Evolving Agent Skill Libraries from Heterogeneous Scientific Resources (2026)  
- [src_7ada95852adce570d6a1] SkillForge: Forging Domain-Specific, Self-Evolving Agent Skills in Cloud Technical Support (2026)  
- [src_efe104582336a2c2377c] SkillLearnBench: Benchmarking Continual Learning Methods for Agent Skill Generation on Real-World Tasks (2026)  
- [src_78741fb5f920631a11d9] MemSkill: Learning and Evolving Memory Skills for Self-Evolving Agents (2026)  
- [src_6f23fd6a05711297118d] AEL: Agent Evolving Learning for Open-Ended Environments (2026)  
- [src_1ec6b2611f09bb621f1e] SEVerA: Verified Synthesis of Self-Evolving Agents (2026)  
- [src_424a6bcfe43138e4c93c] S1-NexusAgent: a Self-Evolving Agent Framework for Multidisciplinary Scientific Research (2026)  
- [src_e761b6bcbbcfcab51cdf] OS-Copilot: Towards Generalist Computer Agents with Self-Improvement (2024)  
- [src_b898768094bd6fa531b5] Evolving Medical Imaging Agents via Experience-driven Self-skill Discovery (2026)  
- [src_a14d3ec9d9267d261539] PsychAgent: An Experience-Driven Lifelong Learning Agent for Self-Evolving Psychological Counselor (2026)  
- [src_61c50dd71b5dab8c226f] Dr. RTL: Autonomous Agentic RTL Optimization through Tool-Grounded Self-Improvement (2026)  
- [src_4c68efd8a0e8767ee6cb] Symbolic Learning Enables Self-Evolving Agents (2024)
