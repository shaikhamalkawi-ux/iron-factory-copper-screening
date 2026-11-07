# Zenodo archive follow-up (not yet published)

The established DOI **10.5281/zenodo.23019081** is an older data/software release. The public GitHub November 2026 code update is not currently associated with a newly verified Zenodo DOI. Do **not** state that the old DOI contains this update.

To mint a version-specific DOI for this revision when authors have approved the release:

1. Sign in to Zenodo and confirm GitHub is connected and this **public** repository is enabled under the Zenodo GitHub integration.
2. Confirm the six-creator metadata and that code (MIT), data/documentation (CC BY 4.0), and any third-party map data are correctly identified.
3. Publish a new GitHub release pointing to the exact approved revision commit. Do not replace or re-label the old v11 deposit.
4. Check the resulting Zenodo record and obtain the **new** version-specific DOI only after it is minted and visible.
5. Update the manuscript's Data Availability Statement and `CITATION.cff` to cite the new exact DOI, while retaining the earlier DOI as a historical version. Get all-author approval before final journal resubmission.

Publishing a GitHub commit by itself does not mint a Zenodo DOI. Automated capture requires the linked repository to be enabled and a subsequent GitHub Release to be published.
