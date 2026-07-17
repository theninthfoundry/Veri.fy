class IRRef:
    """
    A transparent wrapper around any value returned from a tracked SDK call.
    Behaves like the underlying value (str, dict, list) for all normal usage,
    but carries its origin node_id. When an IRRef — or something built from
    one — is passed into another tracked call, the SDK detects the tag and
    emits a MEASURED depends_on edge automatically. No similarity threshold,
    no timestamp guessing.
    """
    __slots__ = ("_value", "_source_node_id", "_source_field")

    def __init__(self, value, source_node_id: str, source_field: str = "content"):
        self._value = value
        self._source_node_id = source_node_id
        self._source_field = source_field

    def __getattr__(self, name):
        return getattr(self._value, name)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __format__(self, format_spec):
        return format(self._value, format_spec)

    def __getitem__(self, key):
        try:
            result = self._value[key]
            return IRRef(result, self._source_node_id, f"{self._source_field}.{key}")
        except Exception:
            return self._value

    def unwrap(self):
        return self._value


def extract_refs(*args, **kwargs) -> list[tuple[str, str]]:
    """
    Walks arguments passed into a tracked call (prompt strings, tool args,
    kwargs dicts) and finds any IRRef instances, returning
    [(source_node_id, source_field), ...]. This is what generates a
    MEASURED depends_on edge, as opposed to an INFERRED one.
    """
    refs = []
    def walk(x):
        if isinstance(x, IRRef):
            refs.append((x._source_node_id, x._source_field))
        elif isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x: walk(v)
    for a in args: walk(a)
    for v in kwargs.values(): walk(v)
    return refs
