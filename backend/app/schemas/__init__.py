"""Request and response models for the v1 API.

Re-exported flat so that ``from app.schemas import DocumentOut`` keeps working
for the endpoints written against the original single-module layout.
"""

from .auth import (
    MessageResponse,
    NormalizedEmail,
    ResendVerificationRequest,
    Token,
    UserCreate,
    UserOut,
    VerifyEmailRequest,
    normalize_email,
)
from .common import BBox, StrictModel
from .document import (
    DocumentDetail,
    DocumentOut,
    JobOut,
    PageOut,
    UploadAccepted,
    UploadRejected,
    UploadResponse,
)
from .parsed import (
    SCHEMA_VERSION,
    DocumentStats,
    DocumentTree,
    PageNode,
    RegionNode,
    WarningNode,
)
from .table import (
    MergeCandidate,
    MergeCandidatesOut,
    MergeTablesRequest,
    RowSource,
    TableCellNode,
    TableMutationResult,
    TableNode,
    TablePart,
)

__all__ = [
    "SCHEMA_VERSION",
    "BBox",
    "DocumentDetail",
    "DocumentOut",
    "DocumentStats",
    "DocumentTree",
    "JobOut",
    "MergeCandidate",
    "MergeCandidatesOut",
    "MergeTablesRequest",
    "MessageResponse",
    "NormalizedEmail",
    "PageNode",
    "PageOut",
    "RegionNode",
    "ResendVerificationRequest",
    "RowSource",
    "StrictModel",
    "TableCellNode",
    "TableMutationResult",
    "TableNode",
    "TablePart",
    "Token",
    "UploadAccepted",
    "UploadRejected",
    "UploadResponse",
    "UserCreate",
    "UserOut",
    "VerifyEmailRequest",
    "WarningNode",
    "normalize_email",
]
