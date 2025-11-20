class NoAudience(Exception):
    def __init__(self, name):
        self.name = name
        super.__init__(f"Audience {name} doesn't exist.")
