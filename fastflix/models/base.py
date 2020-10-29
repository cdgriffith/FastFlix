# -*- coding: utf-8 -*-
class BaseDataClass:
    def __setattr__(self, key, value):
        if value is not None and key in self.__class__.__annotations__:
            annotation = self.__class__.__annotations__[key]
            if hasattr(annotation, "__args__") and getattr(annotation, "_name", "") == "Union":
                annotation = annotation.__args__
            elif hasattr(annotation, "_name"):
                # Assuming this is a typing object we can't handle
                return super().__setattr__(key, value)
            try:
                if not isinstance(value, annotation):
                    raise ValueError(
                        f'"{key}" attempted to be set to "{value}" of type "{type(value)}" but must be of type "{annotation}"'
                    )
            except TypeError as err:
                print(f"Could not validate type for {key}: {err}")
        return super().__setattr__(key, value)
