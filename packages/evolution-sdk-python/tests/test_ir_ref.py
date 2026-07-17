from veri.ir_ref import IRRef, extract_refs

def test_ir_ref_wrapping():
    val = IRRef("some_value", "node_123", "content.output")
    assert str(val) == "some_value"
    assert repr(val) == repr("some_value")
    
    # subscript check
    dict_val = IRRef({"a": {"b": 42}}, "node_123", "content.output")
    assert isinstance(dict_val["a"], IRRef)
    assert dict_val["a"]._source_node_id == "node_123"
    assert dict_val["a"]._source_field == "content.output.a"
    
    assert isinstance(dict_val["a"]["b"], IRRef)
    assert dict_val["a"]["b"]._value == 42
    assert dict_val["a"]["b"]._source_field == "content.output.a.b"

def test_extract_refs():
    ref1 = IRRef("val1", "node_1")
    ref2 = IRRef("val2", "node_2", "metadata")
    
    inputs = {
        "prompt": f"User query: {ref1}",
        "args": [ref2, "plain_string"],
        "nested": {
            "key": ref1
        }
    }
    
    refs = extract_refs(inputs)
    assert ("node_1", "content") in refs
    assert ("node_2", "metadata") in refs
    assert len(refs) == 3
