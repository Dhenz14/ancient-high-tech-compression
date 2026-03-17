# Lazy imports to avoid circular dependency (tokenizer imports config from pipeline)
def __getattr__(name):
    if name == "Compressor":
        from .compressor import Compressor
        return Compressor
    if name == "Decompressor":
        from .decompressor import Decompressor
        return Decompressor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
