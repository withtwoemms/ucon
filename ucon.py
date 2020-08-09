class Unit:
    def __init__(self, name, *aliases):
        self.name = name
        self.aliases = aliases

    def __repr__(self):
        return f'<{self.name}>'
