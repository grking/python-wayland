import griffe

logger = griffe.get_logger(__name__)


class EnumExtension(griffe.Extension):
    """An extension to support enums"""

    def on_class_instance(self, *, node, cls, agent, **kwargs):
        is_enum = cls.bases and str(cls.bases[0]) in ["Enum", "IntFlag"]
        if is_enum:
            cls.extra["mkdocstrings"]["template"] = "enum.html.jinja"
        return super().on_class_instance(node=node, cls=cls, agent=agent, **kwargs)
