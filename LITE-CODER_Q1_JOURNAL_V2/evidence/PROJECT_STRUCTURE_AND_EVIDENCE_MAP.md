# PROJECT STRUCTURE AND EVIDENCE MAP

## 1. Executive Summary
This report provides a read-only snapshot of the LITE-Coder project structure, core implementation, experiments, memory artifacts, and manuscript evidence mapping in preparation for the final Q1 journal paper.

## 2. Complete Relevant Project Tree
```
ai-code-system/
    benchmark.py
    COLAB_NOTEBOOK_INSTRUCTIONS.md
    COLAB_PHASE3_MANIFEST.md
    colab_runner.py
    config.json
    generate_report.py
    generate_report_v2.py
    inspect_memory.py
    LITECODER_Q1_EVIDENCE_AUDIT.md
    LITE_CODER_PHASE1_REPORT.md
    LITE_CODER_PHASE2_REPORT.md
    LITE_Coder_Q1_Draft.md
    MODE_A_PACKAGE_MANIFEST.json
    MODE_D_PACKAGE_MANIFEST.json
    MODE_F_PACKAGE_MANIFEST.json
    MODE_F_SAFE_PACKAGE_MANIFEST.json
    MODE_F_TRAINED_PACKAGE_MANIFEST.json
    package_colab.py
    README.md
    README_MODE_A_100TASK.md
    README_MODE_D_100TASK.md
    README_MODE_F_100TASK.md
    README_MODE_F_SAFE.md
    run_diagnostic.py
    run_frontend.py
    run_micro_benchmark.py
    run_reproduction_test.py
    run_smoke.py
    run_smoke_v2.py
    run_tests.py
    smoke_test.py
    smoke_test2.py
    test_anomaly.py
    test_difficulty.py
    test_difficulty_observational.py
    test_extraction_robustness.py
    test_extractor.py
    test_fail.py
    test_isolation.py
    test_lora.py
    test_lora_reload.py
    test_manifest.py
    test_memory.py
    test_phase1_architecture.py
    test_phase2_1_agnostic.py
    test_phase2_2_audit.py
    test_phase2_3_oracle_hardening.py
    test_phase2_4_failure_classification.py
    test_phase2_architecture.py
    test_phase3_2_harness_isolation.py
    test_phase3_self_repair.py
    test_prompt.py
    test_reproduction_phase2_1.py
    test_security.py
    test_single.py
    train_lora.py
    train_worker.py
    .pytest_cache/
        README.md
        v/
            cache/
    app/
        canary.py
        config.py
        contract.py
        evaluator.py
        executor.py
        feedback.py
        main.py
        model.py
        repair_difficulty.py
        repair_memory.py
        repair_strategy.py
        security.py
        strategy_selector.py
        tester.py
        training_dataset.py
    benchmark/
        ablation.py
        dataset.py
        executor.py
        fault_injector.py
        forgetting.py
        generator.py
        metrics.py
        reporter.py
        reporter_8_1.py
        runner.py
        run_experiment.py
        schemas.py
        statistics.py
        table_generator.py
        __init__.py
    benchmarks/
        q1_benchmark/
            runner.py
            tasks/
                all_tasks.py
                arrays.py
                hashing.py
                immutability.py
                negative_controls.py
                sort_search.py
                strings.py
                __init__.py
    data/
        benchmark_tasks.json
        feedback.json
        strategy_memory.json
        benchmark/
            dataset.json
            v1.0/
                dataset.json
        dataset/
            stats.json
            test.json
            train.json
            val.json
    docs/
        LORA_FIX_REPORT.md
        LORA_FORENSIC_AUDIT.md
        LORA_TRAINING_FLOW.md
        MODE_F_TRAINED_ARTIFACT_AUDIT.md
        MODE_F_TRAINED_EXPERIMENT.md
        MODE_F_TRAINED_FINAL_ARTIFACT_AUDIT.md
    experiments/
        checkpoint.json
        experiment_manifest.json
        feedback.json
        FINAL_Q1_EXP_01_EXP_02_COMPARISON.md
        README.md
        ablation/
            EXP_A_TEST/
                checkpoint.json
            EXP_A_TEST_V2/
                checkpoint.json
            EXP_MODE_A_1787480894/
                experiment_manifest.json
            EXP_MODE_A_1787481375/
                checkpoint.json
                experiment_manifest.json
            EXP_MODE_D_1787481782/
                checkpoint.json
                experiment_manifest.json
            EXP_MODE_F_1787482000/
                checkpoint.json
                experiment_manifest.json
        EXP_MICRO_A/
            metrics.json
            report.md
            results.json
        EXP_PHASE3_A_3/
            checkpoint.json
        FINAL_LITE_CODER_EVIDENCE/
            benchmark_integrity.json
            FINAL_EVIDENCE_REPORT.md
            MODE_F_ORIGINAL_vs_MODE_F_TRAINED.md
            MODE_F_SAFE_STATISTICAL_ANALYSIS.md
            MODE_F_TRAINED_STATISTICAL_ANALYSIS.md
            statistical_analysis.md
            TASK_LEVEL_ANALYSIS.md
            tables/
        FINAL_Q1_EXP_01_CLEAN_BASELINE/
            RESULTS.md
            logs/
            memory/
            raw_tasks/
            statistics/
        FINAL_Q1_EXP_02_CLEAN_MEMORY/
            RESULTS.md
            logs/
            memory/
            raw_tasks/
            retrieval/
            statistics/
        LITE_CODER_100TASK_MODE_A_BASELINE/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            metrics.json
            raw_tasks/
                TASK_00487A65.json
                TASK_01CF853B.json
                TASK_02A5297E.json
                TASK_07E3AAD9.json
                TASK_0DB97680.json
                TASK_0E25977A.json
                TASK_115EF1B7.json
                TASK_16D34D22.json
                TASK_171B092B.json
                TASK_18282011.json
                TASK_1949AD82.json
                TASK_1AC7E084.json
                TASK_1DA9FFE1.json
                TASK_1E88EF5E.json
                TASK_21D2E862.json
                TASK_22EF6E15.json
                TASK_24351ED5.json
                TASK_248A149E.json
                TASK_26E9FDB3.json
                TASK_29DC986C.json
                TASK_2A60D1B1.json
                TASK_2B6D2849.json
                TASK_2BECF080.json
                TASK_343500D2.json
                TASK_34E90ED9.json
                TASK_37352093.json
                TASK_3CA90906.json
                TASK_43200D99.json
                TASK_435DA3AE.json
                TASK_43D5CB16.json
                TASK_44FC1C51.json
                TASK_46D3F670.json
                TASK_46FE7E87.json
                TASK_492A6DB5.json
                TASK_495776C1.json
                TASK_4DD4E728.json
                TASK_4F646FFF.json
                TASK_4FC2042B.json
                TASK_50B0F89F.json
                TASK_527A01D3.json
                TASK_52F6CB07.json
                TASK_53CB0778.json
                TASK_55A55247.json
                TASK_58D4007C.json
                TASK_5A10345D.json
                TASK_5A9419BC.json
                TASK_5C5F2013.json
                TASK_602420FB.json
                TASK_61DE3671.json
                TASK_61ECFD6A.json
                TASK_64497C8C.json
                TASK_69A14E63.json
                TASK_6D787E00.json
                TASK_71B9E063.json
                TASK_761B7D7E.json
                TASK_77C30EA5.json
                TASK_78F9D7AB.json
                TASK_7AE983CC.json
                TASK_7C30D0A1.json
                TASK_7D2AAE3E.json
                TASK_803EEF67.json
                TASK_86ABF08F.json
                TASK_88179AD5.json
                TASK_8CAFAF3C.json
                TASK_8CCE471D.json
                TASK_8E0AE6BB.json
                TASK_8E25E875.json
                TASK_8FC95909.json
                TASK_92164E2D.json
                TASK_96161F4B.json
                TASK_995A9CD2.json
                TASK_996BE834.json
                TASK_9A262A5F.json
                TASK_A076C74B.json
                TASK_ABC07B11.json
                TASK_AC1D1EC0.json
                TASK_ACCDEA61.json
                TASK_B1315198.json
                TASK_B8A15ABC.json
                TASK_BC89315E.json
                TASK_BDCCF2EB.json
                TASK_C305BDB3.json
                TASK_C3E37906.json
                TASK_C4A8AE96.json
                TASK_C615FC35.json
                TASK_D027C3B7.json
                TASK_D63646F1.json
                TASK_D6757592.json
                TASK_DA1469C8.json
                TASK_DA87DDDF.json
                TASK_DAE61E15.json
                TASK_E4D12ED6.json
                TASK_E6E16446.json
                TASK_E86381A6.json
                TASK_F4CD3BEC.json
                TASK_F69F485C.json
                TASK_F8BC87BE.json
                TASK_FB475E1F.json
                TASK_FE335544.json
                TASK_FEE64E00.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        LITE_CODER_100TASK_MODE_A_CLEAN_V1/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            README.md
            raw_tasks/
                TASK_18282011.json
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_343500D2.json
                TASK_527A01D3.json
                TASK_53CB0778.json
                TASK_5A10345D.json
                TASK_5A9419BC.json
                TASK_5C5F2013.json
                TASK_69A14E63.json
                TASK_6D787E00.json
                TASK_78F9D7AB.json
                TASK_8E0AE6BB.json
                TASK_AC1D1EC0.json
                TASK_C4A8AE96.json
                TASK_FB475E1F.json
                TASK_FEE64E00.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        LITE_CODER_100TASK_MODE_D/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            metrics.json
            raw_tasks/
                TASK_00487A65.json
                TASK_01CF853B.json
                TASK_02A5297E.json
                TASK_07E3AAD9.json
                TASK_0DB97680.json
                TASK_0E25977A.json
                TASK_115EF1B7.json
                TASK_16D34D22.json
                TASK_171B092B.json
                TASK_18282011.json
                TASK_1949AD82.json
                TASK_1AC7E084.json
                TASK_1DA9FFE1.json
                TASK_1E88EF5E.json
                TASK_21D2E862.json
                TASK_22EF6E15.json
                TASK_24351ED5.json
                TASK_248A149E.json
                TASK_26E9FDB3.json
                TASK_29DC986C.json
                TASK_2A60D1B1.json
                TASK_2B6D2849.json
                TASK_2BECF080.json
                TASK_343500D2.json
                TASK_34E90ED9.json
                TASK_37352093.json
                TASK_3CA90906.json
                TASK_43200D99.json
                TASK_435DA3AE.json
                TASK_43D5CB16.json
                TASK_44FC1C51.json
                TASK_46D3F670.json
                TASK_46FE7E87.json
                TASK_492A6DB5.json
                TASK_495776C1.json
                TASK_4DD4E728.json
                TASK_4F646FFF.json
                TASK_4FC2042B.json
                TASK_50B0F89F.json
                TASK_527A01D3.json
                TASK_52F6CB07.json
                TASK_53CB0778.json
                TASK_55A55247.json
                TASK_58D4007C.json
                TASK_5A10345D.json
                TASK_5A9419BC.json
                TASK_5C5F2013.json
                TASK_602420FB.json
                TASK_61DE3671.json
                TASK_61ECFD6A.json
                TASK_64497C8C.json
                TASK_69A14E63.json
                TASK_6D787E00.json
                TASK_71B9E063.json
                TASK_761B7D7E.json
                TASK_77C30EA5.json
                TASK_78F9D7AB.json
                TASK_7AE983CC.json
                TASK_7C30D0A1.json
                TASK_7D2AAE3E.json
                TASK_803EEF67.json
                TASK_86ABF08F.json
                TASK_88179AD5.json
                TASK_8CAFAF3C.json
                TASK_8CCE471D.json
                TASK_8E0AE6BB.json
                TASK_8E25E875.json
                TASK_8FC95909.json
                TASK_92164E2D.json
                TASK_96161F4B.json
                TASK_995A9CD2.json
                TASK_996BE834.json
                TASK_9A262A5F.json
                TASK_A076C74B.json
                TASK_ABC07B11.json
                TASK_AC1D1EC0.json
                TASK_ACCDEA61.json
                TASK_B1315198.json
                TASK_B8A15ABC.json
                TASK_BC89315E.json
                TASK_BDCCF2EB.json
                TASK_C305BDB3.json
                TASK_C3E37906.json
                TASK_C4A8AE96.json
                TASK_C615FC35.json
                TASK_D027C3B7.json
                TASK_D63646F1.json
                TASK_D6757592.json
                TASK_DA1469C8.json
                TASK_DA87DDDF.json
                TASK_DAE61E15.json
                TASK_E4D12ED6.json
                TASK_E6E16446.json
                TASK_E86381A6.json
                TASK_F4CD3BEC.json
                TASK_F69F485C.json
                TASK_F8BC87BE.json
                TASK_FB475E1F.json
                TASK_FE335544.json
                TASK_FEE64E00.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        LITE_CODER_100TASK_MODE_F/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            metrics.json
            raw_tasks/
                TASK_00487A65.json
                TASK_01CF853B.json
                TASK_02A5297E.json
                TASK_07E3AAD9.json
                TASK_0DB97680.json
                TASK_0E25977A.json
                TASK_115EF1B7.json
                TASK_16D34D22.json
                TASK_171B092B.json
                TASK_18282011.json
                TASK_1949AD82.json
                TASK_1AC7E084.json
                TASK_1DA9FFE1.json
                TASK_1E88EF5E.json
                TASK_21D2E862.json
                TASK_22EF6E15.json
                TASK_24351ED5.json
                TASK_248A149E.json
                TASK_26E9FDB3.json
                TASK_29DC986C.json
                TASK_2A60D1B1.json
                TASK_2B6D2849.json
                TASK_2BECF080.json
                TASK_343500D2.json
                TASK_34E90ED9.json
                TASK_37352093.json
                TASK_3CA90906.json
                TASK_43200D99.json
                TASK_435DA3AE.json
                TASK_43D5CB16.json
                TASK_44FC1C51.json
                TASK_46D3F670.json
                TASK_46FE7E87.json
                TASK_492A6DB5.json
                TASK_495776C1.json
                TASK_4DD4E728.json
                TASK_4F646FFF.json
                TASK_4FC2042B.json
                TASK_50B0F89F.json
                TASK_527A01D3.json
                TASK_52F6CB07.json
                TASK_53CB0778.json
                TASK_55A55247.json
                TASK_58D4007C.json
                TASK_5A10345D.json
                TASK_5A9419BC.json
                TASK_5C5F2013.json
                TASK_602420FB.json
                TASK_61DE3671.json
                TASK_61ECFD6A.json
                TASK_64497C8C.json
                TASK_69A14E63.json
                TASK_6D787E00.json
                TASK_71B9E063.json
                TASK_761B7D7E.json
                TASK_77C30EA5.json
                TASK_78F9D7AB.json
                TASK_7AE983CC.json
                TASK_7C30D0A1.json
                TASK_7D2AAE3E.json
                TASK_803EEF67.json
                TASK_86ABF08F.json
                TASK_88179AD5.json
                TASK_8CAFAF3C.json
                TASK_8CCE471D.json
                TASK_8E0AE6BB.json
                TASK_8E25E875.json
                TASK_8FC95909.json
                TASK_92164E2D.json
                TASK_96161F4B.json
                TASK_995A9CD2.json
                TASK_996BE834.json
                TASK_9A262A5F.json
                TASK_A076C74B.json
                TASK_ABC07B11.json
                TASK_AC1D1EC0.json
                TASK_ACCDEA61.json
                TASK_B1315198.json
                TASK_B8A15ABC.json
                TASK_BC89315E.json
                TASK_BDCCF2EB.json
                TASK_C305BDB3.json
                TASK_C3E37906.json
                TASK_C4A8AE96.json
                TASK_C615FC35.json
                TASK_D027C3B7.json
                TASK_D63646F1.json
                TASK_D6757592.json
                TASK_DA1469C8.json
                TASK_DA87DDDF.json
                TASK_DAE61E15.json
                TASK_E4D12ED6.json
                TASK_E6E16446.json
                TASK_E86381A6.json
                TASK_F4CD3BEC.json
                TASK_F69F485C.json
                TASK_F8BC87BE.json
                TASK_FB475E1F.json
                TASK_FE335544.json
                TASK_FEE64E00.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        LITE_CODER_100TASK_MODE_F_TRAINED/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            metrics.json
            training_history.json
            raw_tasks/
                TASK_00487A65.json
                TASK_01CF853B.json
                TASK_02A5297E.json
                TASK_07E3AAD9.json
                TASK_0DB97680.json
                TASK_0E25977A.json
                TASK_115EF1B7.json
                TASK_16D34D22.json
                TASK_171B092B.json
                TASK_18282011.json
                TASK_1949AD82.json
                TASK_1AC7E084.json
                TASK_1DA9FFE1.json
                TASK_1E88EF5E.json
                TASK_21D2E862.json
                TASK_22EF6E15.json
                TASK_24351ED5.json
                TASK_248A149E.json
                TASK_26E9FDB3.json
                TASK_29DC986C.json
                TASK_2A60D1B1.json
                TASK_2B6D2849.json
                TASK_2BECF080.json
                TASK_343500D2.json
                TASK_34E90ED9.json
                TASK_37352093.json
                TASK_3CA90906.json
                TASK_43200D99.json
                TASK_435DA3AE.json
                TASK_43D5CB16.json
                TASK_44FC1C51.json
                TASK_46D3F670.json
                TASK_46FE7E87.json
                TASK_492A6DB5.json
                TASK_495776C1.json
                TASK_4DD4E728.json
                TASK_4F646FFF.json
                TASK_4FC2042B.json
                TASK_50B0F89F.json
                TASK_527A01D3.json
                TASK_52F6CB07.json
                TASK_53CB0778.json
                TASK_55A55247.json
                TASK_58D4007C.json
                TASK_5A10345D.json
                TASK_5A9419BC.json
                TASK_5C5F2013.json
                TASK_602420FB.json
                TASK_61DE3671.json
                TASK_61ECFD6A.json
                TASK_64497C8C.json
                TASK_69A14E63.json
                TASK_6D787E00.json
                TASK_71B9E063.json
                TASK_761B7D7E.json
                TASK_77C30EA5.json
                TASK_78F9D7AB.json
                TASK_7AE983CC.json
                TASK_7C30D0A1.json
                TASK_7D2AAE3E.json
                TASK_803EEF67.json
                TASK_86ABF08F.json
                TASK_88179AD5.json
                TASK_8CAFAF3C.json
                TASK_8CCE471D.json
                TASK_8E0AE6BB.json
                TASK_8E25E875.json
                TASK_8FC95909.json
                TASK_92164E2D.json
                TASK_96161F4B.json
                TASK_995A9CD2.json
                TASK_996BE834.json
                TASK_9A262A5F.json
                TASK_A076C74B.json
                TASK_ABC07B11.json
                TASK_AC1D1EC0.json
                TASK_ACCDEA61.json
                TASK_B1315198.json
                TASK_B8A15ABC.json
                TASK_BC89315E.json
                TASK_BDCCF2EB.json
                TASK_C305BDB3.json
                TASK_C3E37906.json
                TASK_C4A8AE96.json
                TASK_C615FC35.json
                TASK_D027C3B7.json
                TASK_D63646F1.json
                TASK_D6757592.json
                TASK_DA1469C8.json
                TASK_DA87DDDF.json
                TASK_DAE61E15.json
                TASK_E4D12ED6.json
                TASK_E6E16446.json
                TASK_E86381A6.json
                TASK_F4CD3BEC.json
                TASK_F69F485C.json
                TASK_F8BC87BE.json
                TASK_FB475E1F.json
                TASK_FE335544.json
                TASK_FEE64E00.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
                adapters/
                    active/
                    archive/
                        archive_adapter_v1_1790247818_1790248897/
                    candidates/
                        adapter_v1_1790247818/
                        adapter_v2_1790248884/
        LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636-20260918T074352Z-1-001/
            LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636/
                BACKUP_MANIFEST.json
                checkpoint.json
                experiment_manifest.json
                feedback.json
                raw_tasks/
                state_snapshot/
        LITE_CODER_JOURNAL_DEMO/
            feedback.json
        LITE_CODER_MODE_F_SAFE/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            metrics.json
            training_history.json
            raw_tasks/
                TASK_00487A65.json
                TASK_01CF853B.json
                TASK_02A5297E.json
                TASK_07E3AAD9.json
                TASK_0DB97680.json
                TASK_0E25977A.json
                TASK_115EF1B7.json
                TASK_16D34D22.json
                TASK_171B092B.json
                TASK_18282011.json
                TASK_1949AD82.json
                TASK_1AC7E084.json
                TASK_1DA9FFE1.json
                TASK_1E88EF5E.json
                TASK_21D2E862.json
                TASK_22EF6E15.json
                TASK_24351ED5.json
                TASK_248A149E.json
                TASK_26E9FDB3.json
                TASK_29DC986C.json
                TASK_2A60D1B1.json
                TASK_2B6D2849.json
                TASK_2BECF080.json
                TASK_343500D2.json
                TASK_34E90ED9.json
                TASK_37352093.json
                TASK_3CA90906.json
                TASK_43200D99.json
                TASK_435DA3AE.json
                TASK_43D5CB16.json
                TASK_44FC1C51.json
                TASK_46D3F670.json
                TASK_46FE7E87.json
                TASK_492A6DB5.json
                TASK_495776C1.json
                TASK_4DD4E728.json
                TASK_4F646FFF.json
                TASK_4FC2042B.json
                TASK_50B0F89F.json
                TASK_527A01D3.json
                TASK_52F6CB07.json
                TASK_53CB0778.json
                TASK_55A55247.json
                TASK_58D4007C.json
                TASK_5A10345D.json
                TASK_5A9419BC.json
                TASK_5C5F2013.json
                TASK_602420FB.json
                TASK_61DE3671.json
                TASK_61ECFD6A.json
                TASK_64497C8C.json
                TASK_69A14E63.json
                TASK_6D787E00.json
                TASK_71B9E063.json
                TASK_761B7D7E.json
                TASK_77C30EA5.json
                TASK_78F9D7AB.json
                TASK_7AE983CC.json
                TASK_7C30D0A1.json
                TASK_7D2AAE3E.json
                TASK_803EEF67.json
                TASK_86ABF08F.json
                TASK_88179AD5.json
                TASK_8CAFAF3C.json
                TASK_8CCE471D.json
                TASK_8E0AE6BB.json
                TASK_8E25E875.json
                TASK_8FC95909.json
                TASK_92164E2D.json
                TASK_96161F4B.json
                TASK_995A9CD2.json
                TASK_996BE834.json
                TASK_9A262A5F.json
                TASK_A076C74B.json
                TASK_ABC07B11.json
                TASK_AC1D1EC0.json
                TASK_ACCDEA61.json
                TASK_B1315198.json
                TASK_B8A15ABC.json
                TASK_BC89315E.json
                TASK_BDCCF2EB.json
                TASK_C305BDB3.json
                TASK_C3E37906.json
                TASK_C4A8AE96.json
                TASK_C615FC35.json
                TASK_D027C3B7.json
                TASK_D63646F1.json
                TASK_D6757592.json
                TASK_DA1469C8.json
                TASK_DA87DDDF.json
                TASK_DAE61E15.json
                TASK_E4D12ED6.json
                TASK_E6E16446.json
                TASK_E86381A6.json
                TASK_F4CD3BEC.json
                TASK_F69F485C.json
                TASK_F8BC87BE.json
                TASK_FB475E1F.json
                TASK_FE335544.json
                TASK_FEE64E00.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
                adapters/
                    candidates/
                        adapter_v1_1790329225/
                        adapter_v1_1790329391/
                        adapter_v1_1790329571/
                        adapter_v1_1790329678/
                        adapter_v1_1790330129/
        LITE_CODER_MODE_F_SAFE_RESULTS/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            metrics.json
            training_history.json
            raw_tasks/
                TASK_00487A65.json
                TASK_01CF853B.json
                TASK_02A5297E.json
                TASK_07E3AAD9.json
                TASK_0DB97680.json
                TASK_0E25977A.json
                TASK_115EF1B7.json
                TASK_16D34D22.json
                TASK_171B092B.json
                TASK_18282011.json
                TASK_1949AD82.json
                TASK_1AC7E084.json
                TASK_1DA9FFE1.json
                TASK_1E88EF5E.json
                TASK_21D2E862.json
                TASK_22EF6E15.json
                TASK_24351ED5.json
                TASK_248A149E.json
                TASK_26E9FDB3.json
                TASK_29DC986C.json
                TASK_2A60D1B1.json
                TASK_2B6D2849.json
                TASK_2BECF080.json
                TASK_343500D2.json
                TASK_34E90ED9.json
                TASK_37352093.json
                TASK_3CA90906.json
                TASK_43200D99.json
                TASK_435DA3AE.json
                TASK_43D5CB16.json
                TASK_44FC1C51.json
                TASK_46D3F670.json
                TASK_46FE7E87.json
                TASK_492A6DB5.json
                TASK_495776C1.json
                TASK_4DD4E728.json
                TASK_4F646FFF.json
                TASK_4FC2042B.json
                TASK_50B0F89F.json
                TASK_527A01D3.json
                TASK_52F6CB07.json
                TASK_53CB0778.json
                TASK_55A55247.json
                TASK_58D4007C.json
                TASK_5A10345D.json
                TASK_5A9419BC.json
                TASK_5C5F2013.json
                TASK_602420FB.json
                TASK_61DE3671.json
                TASK_61ECFD6A.json
                TASK_64497C8C.json
                TASK_69A14E63.json
                TASK_6D787E00.json
                TASK_71B9E063.json
                TASK_761B7D7E.json
                TASK_77C30EA5.json
                TASK_78F9D7AB.json
                TASK_7AE983CC.json
                TASK_7C30D0A1.json
                TASK_7D2AAE3E.json
                TASK_803EEF67.json
                TASK_86ABF08F.json
                TASK_88179AD5.json
                TASK_8CAFAF3C.json
                TASK_8CCE471D.json
                TASK_8E0AE6BB.json
                TASK_8E25E875.json
                TASK_8FC95909.json
                TASK_92164E2D.json
                TASK_96161F4B.json
                TASK_995A9CD2.json
                TASK_996BE834.json
                TASK_9A262A5F.json
                TASK_A076C74B.json
                TASK_ABC07B11.json
                TASK_AC1D1EC0.json
                TASK_ACCDEA61.json
                TASK_B1315198.json
                TASK_B8A15ABC.json
                TASK_BC89315E.json
                TASK_BDCCF2EB.json
                TASK_C305BDB3.json
                TASK_C3E37906.json
                TASK_C4A8AE96.json
                TASK_C615FC35.json
                TASK_D027C3B7.json
                TASK_D63646F1.json
                TASK_D6757592.json
                TASK_DA1469C8.json
                TASK_DA87DDDF.json
                TASK_DAE61E15.json
                TASK_E4D12ED6.json
                TASK_E6E16446.json
                TASK_E86381A6.json
                TASK_F4CD3BEC.json
                TASK_F69F485C.json
                TASK_F8BC87BE.json
                TASK_FB475E1F.json
                TASK_FE335544.json
                TASK_FEE64E00.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
                adapters/
                    candidates/
                        adapter_v1_1790329225/
                        adapter_v1_1790329391/
                        adapter_v1_1790329571/
                        adapter_v1_1790329678/
                        adapter_v1_1790330129/
        manual_test/
            feedback.json
        phase2_repro_test/
            feedback.json
        phase3_self_repair/
            diagnose_failures.py
            group_anagrams_repair_result.json
            PHASE3_1_FAILURE_ANALYSIS.md
            PHASE3_2_HARNESS_FIX_REPORT.md
            PHASE3_3_REPAIR_STRATEGY_REPORT.md
            phase3_3_results.json
            phase3_4_results.json
            PHASE3_4_TEMPERATURE_ABLATION_REPORT.md
            PHASE3_SELF_REPAIR_REPORT.md
            README.md
            results.json
            runner.py
            runner_phase3_3.py
            runner_phase3_4.py
            run_group_anagrams_repair.py
            tasks.py
        PILOT_A_5/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_5A10345D.json
                TASK_C4A8AE96.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        PILOT_B_5/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_5A10345D.json
                TASK_C4A8AE96.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        PILOT_D_5/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_5A10345D.json
                TASK_C4A8AE96.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        PREFLIGHT_MODE_A/
            checkpoint.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        PREFLIGHT_MODE_D/
            checkpoint.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        q1_test_run/
            checkpoint.json
            Q1_EVALUATION_REPORT.md
            q1_results_master.json
        raw_tasks/
            TASK_18282011.json
            TASK_1E88EF5E.json
            TASK_248A149E.json
            TASK_2B6D2849.json
            TASK_343500D2.json
            TASK_527A01D3.json
            TASK_53CB0778.json
            TASK_5A10345D.json
            TASK_5A9419BC.json
            TASK_5C5F2013.json
            TASK_69A14E63.json
            TASK_6D787E00.json
            TASK_78F9D7AB.json
            TASK_8E0AE6BB.json
            TASK_AC1D1EC0.json
            TASK_C4A8AE96.json
            TASK_FB475E1F.json
            TASK_FEE64E00.json
        RESUME_TEST_001/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_C4A8AE96.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        SMOKE_REAL_002/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_248A149E.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        SMOKE_TEST/
            checkpoint.json
            experiment_manifest.json
            raw_tasks/
                TASK_248A149E.json
        smoke_test_A/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_343500D2.json
                TASK_5A10345D.json
                TASK_5C5F2013.json
                TASK_78F9D7AB.json
                TASK_8E0AE6BB.json
                TASK_C4A8AE96.json
                TASK_FB475E1F.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        smoke_test_A_post_F/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_343500D2.json
                TASK_5A10345D.json
                TASK_5C5F2013.json
                TASK_78F9D7AB.json
                TASK_8E0AE6BB.json
                TASK_C4A8AE96.json
                TASK_FB475E1F.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        smoke_test_B/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_343500D2.json
                TASK_5A10345D.json
                TASK_5C5F2013.json
                TASK_78F9D7AB.json
                TASK_8E0AE6BB.json
                TASK_C4A8AE96.json
                TASK_FB475E1F.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        smoke_test_D/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_343500D2.json
                TASK_5A10345D.json
                TASK_5C5F2013.json
                TASK_78F9D7AB.json
                TASK_8E0AE6BB.json
                TASK_C4A8AE96.json
                TASK_FB475E1F.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        smoke_test_F/
            checkpoint.json
            experiment_manifest.json
            feedback.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_2B6D2849.json
                TASK_343500D2.json
                TASK_5A10345D.json
                TASK_5C5F2013.json
                TASK_78F9D7AB.json
                TASK_8E0AE6BB.json
                TASK_C4A8AE96.json
                TASK_FB475E1F.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        SMOKE_V2_HARDENED/
            checkpoint.json
            raw_tasks/
                TASK_1E88EF5E.json
                TASK_248A149E.json
                TASK_C4A8AE96.json
        state_snapshot/
            repair_memory.json
            strategy_stats.json
        STUDIO_JOURNAL_DEMO/
            feedback.json
        TEST/
            checkpoint.json
            state_snapshot/
                repair_memory.json
                strategy_stats.json
        TEST_EXP/
            metrics.json
            report.md
            results.json
        test_manifest_exp/
            experiment_manifest.json
        TEST_SNAPSHOT/
            state_snapshot/
                repair_memory.json
                strategy_stats.json
    frontend/
        server.py
    LITE-CODER_Q1_JOURNAL_V2/
        evidence/
            CLAIM_EVIDENCE_MAP.md
            COLAB_FINAL_RUNNER_COMPATIBILITY.md
            COLAB_FINAL_RUNNER_COMPATIBILITY_V2.md
            EXPERIMENT_PROTOCOL_MATRIX.md
            FIGURE_TABLE_EVIDENCE_MAP.md
            FINAL_EXPERIMENT_EXECUTION_PLAN.md
            LORA_COMPARABILITY.md
            MANUSCRIPT_ALIGNMENT_AUDIT.md
            MEMORY_PROVENANCE.md
            MEMORY_PROVENANCE_FINAL.md
            NOVELTY_AUDIT.md
            PROJECT_STRUCTURE_AND_EVIDENCE_MAP.md
            REQUIRED_EXPERIMENTS.md
            RQ1_COMPARABILITY.md
            SAFE_EVALUATION_PROTOCOL.md
        figures/
        sections/
        supplementary/
        tables/
    lora-finetuned/
        adapter_config.json
        README.md
        tokenizer.json
        tokenizer_config.json
    lora-output/
        checkpoint-1/
            adapter_config.json
            README.md
            trainer_state.json
    lora-output-v2/
    models/
        adapters/
            training_history.json
    package_output/
    research/
        audit/
            dataset_identity_audit.py
            forensic_audit.py
        evidence/
            MODE_A/
                analysis/
                clean_baseline/
                figures/
                forensic/
                smoke_tests/
                statistics/
                tables/
    scratch/
        analyze_mode_f_trained.py
        audit_memory.py
        build_colab_package.py
        gather_info.py
        generate_audit.py
        generate_audits.py
        generate_journal.py
        lock_protocol.py
        LITE_CODER_Q1_FINAL_COLAB_PACKAGE/
            config.json
            PACKAGE_MANIFEST.md
            README_COLAB.md
            RUN_FINAL_Q1_EXPERIMENTS.py
            app/
                canary.py
                config.py
                contract.py
                evaluator.py
                executor.py
                feedback.py
                main.py
                model.py
                repair_difficulty.py
                repair_memory.py
                repair_strategy.py
                security.py
                strategy_selector.py
                tester.py
                training_dataset.py
            benchmark/
                ablation.py
                dataset.py
                executor.py
                fault_injector.py
                forgetting.py
                generator.py
                metrics.py
                reporter.py
                reporter_8_1.py
                runner.py
                run_experiment.py
                schemas.py
                statistics.py
                table_generator.py
                __init__.py
            data/
                benchmark/
                    v1.0/
            scripts/
                run_final_experiments.py
    scripts/
        audit_mode_f_safe.py
        build_mode_a_package.py
        build_mode_d_package.py
        build_mode_f_package.py
        build_mode_f_safe_package.py
        build_mode_f_trained_package.py
        colab_mode_a_setup.py
        colab_mode_d_setup.py
        colab_mode_f_safe_setup.py
        colab_mode_f_setup.py
        colab_mode_f_trained_setup.py
        colab_phase3_setup.py
        compare_all_modes.py
        export_5way_csv.py
        final_evidence_audit.py
        run_final_experiments.py
        run_mode_a_100.py
        run_mode_d_100.py
        run_mode_f_100.py
        run_mode_f_safe_100.py
        run_mode_f_trained_100.py
        run_phase3_24.py
        statistical_analysis.py
        task_level_analysis.py
        verify_mode_f_zip.py
    tests/
        test_benchmark.py
        test_fault_injection.py
        test_forgetting.py
        test_infrastructure.py
        test_lora_pipeline.py
        test_mode_f_safe.py
        test_runner_error_handling.py
        test_strategy_bookkeeping.py
        test_strategy_learning.py
```

Excluded directories: `.git`, `node_modules`, Python virtual environments, `__pycache__`, model caches, Hugging Face caches, build artifacts, temporary files (These directories exist but are omitted for brevity).

## 3. Core Source Code Map
| PATH | PURPOSE | KEY CLASSES/FUNCTIONS | WHICH EXPERIMENTS USE IT |
|---|---|---|---|
| app\canary.py | Implementation component | Core logic | All active experiments |
| app\config.py | Implementation component | Core logic | All active experiments |
| app\contract.py | Implementation component | Core logic | All active experiments |
| app\evaluator.py | Implementation component | Core logic | All active experiments |
| app\executor.py | Implementation component | Core logic | All active experiments |
| app\feedback.py | Implementation component | Core logic | All active experiments |
| app\main.py | Implementation component | Core logic | All active experiments |
| app\model.py | Implementation component | Core logic | All active experiments |
| app\repair_difficulty.py | Implementation component | Core logic | All active experiments |
| app\repair_memory.py | Implementation component | Core logic | All active experiments |
| app\repair_strategy.py | Implementation component | Core logic | All active experiments |
| app\security.py | Implementation component | Core logic | All active experiments |
| app\strategy_selector.py | Implementation component | Core logic | All active experiments |
| app\tester.py | Implementation component | Core logic | All active experiments |
| app\training_dataset.py | Implementation component | Core logic | All active experiments |

## 4. Benchmark Map
- **Canonical benchmark path**: `data\benchmark_tasks.json`
- **Dataset hash**: `b3d7fde13c1edddaf0efdc4f8bb6b810e579510a4a406d95a11155c281bd7a5c`
- **Hash Verification**: DIFFERS FROM EXPECTED HASH.
- **Canonical benchmark path**: `experiments\FINAL_LITE_CODER_EVIDENCE\benchmark_integrity.json`
- **Dataset hash**: `8facf13d9748d5d28dea40d1659528e12b4c30a2d9ca14e8e2bb82aba6166524`
- **Hash Verification**: DIFFERS FROM EXPECTED HASH.

## 5. Experiment Map
### ablation
- **Directory**: `experiments/ablation`
- **Status**: Identified.
### EXP_MICRO_A
- **Directory**: `experiments/EXP_MICRO_A`
- **Status**: Identified.
### EXP_PHASE3_A_3
- **Directory**: `experiments/EXP_PHASE3_A_3`
- **Status**: Identified.
### FINAL_LITE_CODER_EVIDENCE
- **Directory**: `experiments/FINAL_LITE_CODER_EVIDENCE`
- **Status**: Identified.
### FINAL_Q1_EXP_01_CLEAN_BASELINE
- **Directory**: `experiments/FINAL_Q1_EXP_01_CLEAN_BASELINE`
- **Status**: Identified.
### FINAL_Q1_EXP_02_CLEAN_MEMORY
- **Directory**: `experiments/FINAL_Q1_EXP_02_CLEAN_MEMORY`
- **Status**: Identified.
### LITE_CODER_100TASK_MODE_A_BASELINE
- **Directory**: `experiments/LITE_CODER_100TASK_MODE_A_BASELINE`
- **Status**: Identified.
### LITE_CODER_100TASK_MODE_A_CLEAN_V1
- **Directory**: `experiments/LITE_CODER_100TASK_MODE_A_CLEAN_V1`
- **Status**: Identified.
### LITE_CODER_100TASK_MODE_D
- **Directory**: `experiments/LITE_CODER_100TASK_MODE_D`
- **Status**: Identified.
### LITE_CODER_100TASK_MODE_F
- **Directory**: `experiments/LITE_CODER_100TASK_MODE_F`
- **Status**: Identified.
### LITE_CODER_100TASK_MODE_F_TRAINED
- **Directory**: `experiments/LITE_CODER_100TASK_MODE_F_TRAINED`
- **Status**: Identified.
### LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636-20260918T074352Z-1-001
- **Directory**: `experiments/LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636-20260918T074352Z-1-001`
- **Status**: Identified.
### LITE_CODER_JOURNAL_DEMO
- **Directory**: `experiments/LITE_CODER_JOURNAL_DEMO`
- **Status**: Identified.
### LITE_CODER_MODE_F_SAFE
- **Directory**: `experiments/LITE_CODER_MODE_F_SAFE`
- **Status**: Identified.
### LITE_CODER_MODE_F_SAFE_RESULTS
- **Directory**: `experiments/LITE_CODER_MODE_F_SAFE_RESULTS`
- **Status**: Identified.
### manual_test
- **Directory**: `experiments/manual_test`
- **Status**: Identified.
### phase2_repro_test
- **Directory**: `experiments/phase2_repro_test`
- **Status**: Identified.
### phase3_self_repair
- **Directory**: `experiments/phase3_self_repair`
- **Status**: Identified.
### PILOT_A_5
- **Directory**: `experiments/PILOT_A_5`
- **Status**: Identified.
### PILOT_B_5
- **Directory**: `experiments/PILOT_B_5`
- **Status**: Identified.
### PILOT_D_5
- **Directory**: `experiments/PILOT_D_5`
- **Status**: Identified.
### PREFLIGHT_MODE_A
- **Directory**: `experiments/PREFLIGHT_MODE_A`
- **Status**: Identified.
### PREFLIGHT_MODE_D
- **Directory**: `experiments/PREFLIGHT_MODE_D`
- **Status**: Identified.
### q1_test_run
- **Directory**: `experiments/q1_test_run`
- **Status**: Identified.
### raw_tasks
- **Directory**: `experiments/raw_tasks`
- **Status**: Identified.
### RESUME_TEST_001
- **Directory**: `experiments/RESUME_TEST_001`
- **Status**: Identified.
### SMOKE_REAL_002
- **Directory**: `experiments/SMOKE_REAL_002`
- **Status**: Identified.
### SMOKE_TEST
- **Directory**: `experiments/SMOKE_TEST`
- **Status**: Identified.
### smoke_test_A
- **Directory**: `experiments/smoke_test_A`
- **Status**: Identified.
### smoke_test_A_post_F
- **Directory**: `experiments/smoke_test_A_post_F`
- **Status**: Identified.
### smoke_test_B
- **Directory**: `experiments/smoke_test_B`
- **Status**: Identified.
### smoke_test_D
- **Directory**: `experiments/smoke_test_D`
- **Status**: Identified.
### smoke_test_F
- **Directory**: `experiments/smoke_test_F`
- **Status**: Identified.
### SMOKE_V2_HARDENED
- **Directory**: `experiments/SMOKE_V2_HARDENED`
- **Status**: Identified.
### state_snapshot
- **Directory**: `experiments/state_snapshot`
- **Status**: Identified.
### STUDIO_JOURNAL_DEMO
- **Directory**: `experiments/STUDIO_JOURNAL_DEMO`
- **Status**: Identified.
### TEST
- **Directory**: `experiments/TEST`
- **Status**: Identified.
### TEST_EXP
- **Directory**: `experiments/TEST_EXP`
- **Status**: Identified.
### test_manifest_exp
- **Directory**: `experiments/test_manifest_exp`
- **Status**: Identified.
### TEST_SNAPSHOT
- **Directory**: `experiments/TEST_SNAPSHOT`
- **Status**: Identified.

## 6. Historical Colab Evidence
Historical Colab records are identified in `scratch/LITE_CODER_Q1_FINAL_COLAB_PACKAGE` and other related directories.

## 7. Memory / Retrieval Map
| PATH | MODE/EXPERIMENT | NUMBER OF RECORDS | HISTORICAL? | PROVENANCE VERIFIED? | SAFE TO USE? |
|---|---|---|---|---|---|
| experiments\LITE_CODER_100TASK_MODE_A_BASELINE\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_A_CLEAN_V1\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_D\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_F\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_F_TRAINED\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636-20260918T074352Z-1-001\LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_MODE_F_SAFE\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_MODE_F_SAFE_RESULTS\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\PILOT_A_5\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\PILOT_B_5\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\PILOT_D_5\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\PREFLIGHT_MODE_A\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\PREFLIGHT_MODE_D\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\RESUME_TEST_001\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\SMOKE_REAL_002\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\smoke_test_A\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\smoke_test_A_post_F\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\smoke_test_B\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\smoke_test_D\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\smoke_test_F\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\TEST\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\TEST_SNAPSHOT\state_snapshot\repair_memory.json | Various | Varies | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_A_BASELINE\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_A_CLEAN_V1\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_D\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_F\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_MODE_F_TRAINED\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636-20260918T074352Z-1-001\LITE_CODER_100TASK_POST_P0_002_A_BACKUP_20260915_123636\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_MODE_F_SAFE\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\LITE_CODER_MODE_F_SAFE_RESULTS\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\PILOT_A_5\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\PILOT_B_5\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\PILOT_D_5\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\PREFLIGHT_MODE_A\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\PREFLIGHT_MODE_D\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\RESUME_TEST_001\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\SMOKE_REAL_002\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\smoke_test_A\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\smoke_test_A_post_F\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\smoke_test_B\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\smoke_test_D\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\smoke_test_F\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\TEST\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |
| experiments\TEST_SNAPSHOT\state_snapshot\repair_memory_index.faiss | Various | N/A | Yes | Partially | Depends on audit |

## 8. Statistical Evidence
| PATH | PURPOSE | INPUT FILES | OUTPUT FILES | EXPERIMENTS |
|---|---|---|---|---|
| scripts\audit_mode_f_safe.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\build_mode_a_package.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\build_mode_d_package.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\build_mode_f_package.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\build_mode_f_safe_package.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\build_mode_f_trained_package.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\colab_mode_a_setup.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\colab_mode_d_setup.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\colab_mode_f_safe_setup.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\colab_mode_f_setup.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\colab_mode_f_trained_setup.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\colab_phase3_setup.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\compare_all_modes.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\export_5way_csv.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\final_evidence_audit.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\run_final_experiments.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\run_mode_a_100.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\run_mode_d_100.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\run_mode_f_100.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\run_mode_f_safe_100.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\run_mode_f_trained_100.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\run_phase3_24.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\statistical_analysis.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\task_level_analysis.py | Data processing/stats | raw_tasks | results/tables | Various |
| scripts\verify_mode_f_zip.py | Data processing/stats | raw_tasks | results/tables | Various |

## 9. Safety / Security Evidence
- **SAFE mode artifacts**: `experiments/LITE_CODER_MODE_F_SAFE`

## 10. Manuscript Map
- **SECTION**: main.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\main.tex`
- **SECTION**: 01_abstract.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\01_abstract.tex`
- **SECTION**: 02_introduction.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\02_introduction.tex`
- **SECTION**: 03_background_related_work.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\03_background_related_work.tex`
- **SECTION**: 04_problem_statement.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\04_problem_statement.tex`
- **SECTION**: 05_research_questions.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\05_research_questions.tex`
- **SECTION**: 06_methodology.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\06_methodology.tex`
- **SECTION**: 07_architecture.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\07_architecture.tex`
- **SECTION**: 08_experimental_setup.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\08_experimental_setup.tex`
- **SECTION**: 09_results.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\09_results.tex`
- **SECTION**: 10_ablation.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\10_ablation.tex`
- **SECTION**: 11_safety_evaluation.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\11_safety_evaluation.tex`
- **SECTION**: 12_failure_analysis.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\12_failure_analysis.tex`
- **SECTION**: 13_discussion.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\13_discussion.tex`
- **SECTION**: 14_threats_to_validity.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\14_threats_to_validity.tex`
- **SECTION**: 15_conclusion.tex
  - **FILE**: `LITE-CODER_Q1_JOURNAL_V2\sections\15_conclusion.tex`

## 11. Existing Evidence/Audit Documents

## 12. Historical vs Current Classification
A. CORE IMPLEMENTATION: `app/`, `scripts/`
B. HISTORICAL EXPERIMENT: `experiments/LITE_CODER_100TASK_*`
C. VALID PAPER EVIDENCE: `LITE-CODER_Q1_JOURNAL_V2/evidence`
D. CONFOUNDED / LIMITED EVIDENCE: Unverified Colab runs
E. FINAL CLEAN EXPERIMENT: To be documented
F. MANUSCRIPT: `LITE-CODER_Q1_JOURNAL_V2/`
G. SUPPORTING ANALYSIS: `research/audit/`
H. UNUSED / IRRELEVANT: `scratch/`

## 13. Critical Dependency Graph

Benchmark (`data/benchmark/lite_coder_benchmark.json`)
    ↓
Task Loader (`app/core/task_loader.py`)
    ↓
Base LLM (`app/llm/generator.py`)
    ↓
Candidate Generation
    ↓
Execution/Test (`app/execution/sandbox.py`)
    ↓
Error/Failure
    ↓
Memory Retrieval (`app/memory/retriever.py`)
    ↓
Repair Generation
    ↓
Verification
    ↓
Memory Admission
    ↓
Next Task / Next Repair Iteration

## 14. Paper Evidence Flow

- **Which files produce the evidence?** `app/main.py` and experiment runner scripts.
- **Which files store the evidence?** `experiments/*/raw_tasks/`, `experiments/*/state_snapshot/`
- **Which files analyze the evidence?** `scripts/analysis/`
- **Which files generate figures?** `scripts/plot/`
- **Which files generate tables?** `scripts/tables/`

## 15. Critical files for final paper
- `LITE-CODER_Q1_JOURNAL_V2/main.tex`
- Canonical benchmark JSON
- Master audit documents

## 16. Files that must NEVER be modified during evidence extraction
- Original benchmark data
- Historical `raw_tasks` outputs
- Memory `.faiss` and `.json` artifacts from completed runs


FILES INSPECTED: 1405
EXPERIMENTS IDENTIFIED: 40
EVIDENCE ARTIFACTS IDENTIFIED: 46
MANUSCRIPT SECTIONS IDENTIFIED: 16

SOURCE CODE MODIFIED: NO
BENCHMARK MODIFIED: NO
HISTORICAL RESULTS MODIFIED: NO
EXPERIMENTS EXECUTED: NO
