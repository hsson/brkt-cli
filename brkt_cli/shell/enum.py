class Enum:
    @classmethod
    def format_enum(cls, enum):
        """
        Formats an enum as a string
        :param enum: the enum integer
        :type enum: int
        :return: the string name of the enum
        :rtype: unicode
        """
        for val in filter((lambda (key, value): not key.startswith('__')), cls.__dict__.items()):
            if val[1] == enum:
                return val[0]
