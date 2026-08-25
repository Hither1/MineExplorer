"""The world-model agent's mechanism, ported from MCU-AgentBeats' `mcu_worldmodel`.

Module map (files mirror the MCU names so the two trees diff cleanly):

    memory.py      the multimodal filesystem that is the agent's memory
    hypotheses.py  the belief DAG, on disk, with a bounded prompt view
    discipline.py  the warden: env-verified goals, claim gate, test budgets
    milestones.py  the ground-truth ledger (verified by the harness's checker)
    actions.py     actions.json parsing: raw entries + procedure entries, tick-budgeted
    procedures.py  the macro library and its closed-loop markers
    camera.py      camera-delta chunking (quantisation seam, unused on this env)
    prompts.py     the act turn and the induction turn
    agent.py       WorldModelCore: the dual-turn loop itself

The harness-facing adapter is mc_agent/worldmodel_agent.py.
"""
