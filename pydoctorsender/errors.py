# define our Doctorsender exceptions
class Error(Exception):
    """Base class for other exceptions."""
    pass


class DrsSegmentError(Error):
    """Raised when the Segment does not exist or is wrongfully constructed."""
    pass


class DrsListError(Error):
    """Raised when a List is called that does not exist."""
    pass


class DrsReturnError(Error):
    """Raised when Doctorsender returns an Error."""
    pass


class DrsCampaignError(Error):
    """Raised when Doctorsender returns an Error."""
    pass


class DrsParserError(Error):
    """Raised when the Doctorsender Response can not be parsed."""
    pass
