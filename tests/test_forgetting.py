import pytest
from benchmark.schemas import BenchmarkTask

def test_anchor_set_isolation():
    # Simulated anchor set
    anchors = [BenchmarkTask(task_id="A1", category="logic", difficulty="EASY", prompt="Fix this")]
    train_set = [BenchmarkTask(task_id="T1", category="logic", difficulty="EASY", prompt="Fix that")]
    
    # Ensure no overlap
    anchor_ids = {t.task_id for t in anchors}
    train_ids = {t.task_id for t in train_set}
    
    assert anchor_ids.isdisjoint(train_ids)
