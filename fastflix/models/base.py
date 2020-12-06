# -*- coding: utf-8 -*-
import logging
from multiprocessing import Queue

logger = logging.getLogger("fastflix")

ignore_list = [Queue]

NO_OPTION = object()


class BaseDataClass:
    def __setattr__(self, key, value):
        if value is not None and key in self.__class__.__annotations__:
            annotation = self.__class__.__annotations__[key]
            if hasattr(annotation, "__args__") and getattr(annotation, "_name", "") == "Union":
                annotation = annotation.__args__
            elif hasattr(annotation, "_name"):
                # Assuming this is a typing object we can't handle
                return super().__setattr__(key, value)
            if annotation in ignore_list:
                return super().__setattr__(key, value)
            try:
                if not isinstance(value, annotation):
                    raise ValueError(
                        f'"{key}" attempted to be set to "{value}" of type "{type(value)}" but must be of type "{annotation}"'
                    )
            except TypeError as err:
                logger.debug(f"Could not validate type for {key} with {annotation}: {err}")
        return super().__setattr__(key, value)

    def get(self, item, default=NO_OPTION):
        if default != NO_OPTION:
            return getattr(self, item, default)
        return getattr(self, item)
