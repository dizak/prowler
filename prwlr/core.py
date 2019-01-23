import pandas as _pd
import numpy as _np
from . import databases
from . import profiles as _profiles

class Columns:
    """
    Container for the columns names defined in this module.
    """
    SPLIT_SUF = '_SPLIT'
    REF = 'REF'
    QRY = 'QRY'
    REF_SPLIT = '{}{}'.format(REF, SPLIT_SUF)
    QRY_SPLIT = '{}{}'.format(QRY, SPLIT_SUF)

def get_IDs_names(
    species,
):
    """
    Returns dict of KEGG Organism IDs as keys and biological names as values.

    Parameters
    -------
    species: list of str
        List of full biological names to convert into KEGG Organism IDs.

    Returns
    ------
    dict
    """
    kegg_db = databases.KEGG('Orthology')
    kegg_db.parse_organism_info(
        organism=None,
        reference_species=species,
        IDs=None,
        X_ref=None,
        KOs=None,
        IDs_only=True,
    )
    return {k.lower(): v for k, v in kegg_db.ID_name.items()}

def profilize_organism(
    organism,
    species,
    IDs=None,
    X_ref=None,
    KOs=None,
):
    """
    Returns pandas.DataFrame with Phylogenetic Profile for each ORF name of an
    organism.

    Parameters
    -------
    organism: str
        Full biological name of the organism.
    species: list of str
        List of full biological names to build the Phylogenetic Profile.
    IDs: str, path
        Filename of the KEGG Organism IDs. Downloaded to a temporary file if
        <None>.
    X_ref: str, path
        Filename of the ORF-KEGG Orthology Group cross-reference.
        Downloaded to a temporary file if <None>.
    KOs: str, path
        Filename of the KEGG Orthology Group-Organism cross-reference.
        Downloaded to a temporary file if <None>.

    Returns
    ------
    pandas.DataFrame
    """
    kegg_db = databases.KEGG('Orthology')
    kegg_db.parse_organism_info(
        organism=organism,
        reference_species=species,
        IDs=IDs,
        X_ref=X_ref,
        KOs=KOs,
    )
    return kegg_db.organism_info.drop(columns=databases.Columns.KEGG_ID)

def read_sga(
    filename,
    version=2,
):
    """
    Returns pandas.DataFrame with Genetic Interaction Network from
    the Costanzo's SGA experiment either version 1 or 2.

    Parameters
    -------
    filename: str, path
        Filename of the SGA.
    version: int
        Version number of the Costanzo's SGA experiment. 1 or 2 available.

    Returns
    -------
    pandas.DataFrame
    """
    if version == 1:
        sga = databases.SGA1()
    elif version == 2:
        sga = databases.SGA2()
    else:
        raise errors.ParserError("Only versions 1 and 2 of Costanzo's SGA experiment are supported.")
    sga.parse(filename=filename)
    return sga.sga

def read_profiles(
    filename,
    reference_column=Columns.REF,
    query_column=Columns.QRY,
    str_sep='|',
    **kwargs
):
    """
    Returns pandas.Series with prwlr.profiles.Profile objects from CSV.

    Parameters
    -------
    filename: str, path
        Filename of the CSV.
    """
    ref_qry_df = _pd.read_csv(filename, **kwargs)
    ref_qry_df[Columns.REF_SPLIT] = ref_qry_df[Columns.REF].str.split(str_sep)
    ref_qry_df[Columns.QRY_SPLIT] = ref_qry_df[Columns.QRY].str.split(str_sep)
    return ref_qry_df[[Columns.REF_SPLIT, Columns.QRY_SPLIT]].apply(
        lambda x: _profiles.Profile(
            reference=x[Columns.REF_SPLIT],
            query=x[Columns.QRY_SPLIT],
        ),
        axis=1,
    )

def save_profiles(
    series,
    filename,
    reference_column=Columns.REF,
    query_column=Columns.QRY,
    str_sep='|',
    **kwargs
):
    """
    Writes pandas.Series with prwlr.profiles.Profile objects to CSV file.

    Parameters
    -------
    Filename: str, path
        Name of the file.
    """
    _pd.DataFrame(
        {
            Columns.REF: series.apply(lambda x: x.reference).str.join(str_sep),
            Columns.QRY: series.apply(lambda x: x.query).str.join(str_sep),
        },
    ).to_csv(filename, **kwargs)

def merge_sga_profiles(
    sga,
    profiles
):
    """
    Returns Genetic Interaction Network from the Costanzo's SGA experiment with
    Phylogenetic Profiles.
    """
    merged = _pd.merge(
        left=sga,
        right=profiles,
        left_on=databases.Columns.ORF_Q,
        right_on=databases.Columns.ORF_ID,
        how="left",
    ).merge(
        right=profiles,
        left_on=databases.Columns.ORF_A,
        right_on=databases.Columns.ORF_ID,
        how="left",
        suffixes=(
            databases.Columns.QUERY_SUF,
            databases.Columns.ARRAY_SUF,
        )
    )
    merged.drop(
        columns=[
            databases.Columns.ORF_ID_Q,
            databases.Columns.ORF_ID_A,
        ],
        axis=1,
        inplace=True,
    )
    merged.dropna(inplace=True)
    merged.reset_index(
        drop=True,
        inplace=True,
    )
    return merged

def calculate_pss(
    network,
    method,
):
    """
    Returns Genetic Interaction Network from the Costanzo's SGA experiment with
    Profiles Similarity Score.

    Parameters
    -------
    network: pandas.DataFrame
    method: str

    Returns
    -------
    pandas.DataFrame
    """
    if method == 'pairwise':
        def pss(ar1, ar2):
            return sum(a == b for a, b in zip(ar1, ar2))
        pss_vect = _np.vectorize(pss)
        network[databases.Columns.PSS] = pss_vect(
            network[databases.Columns.PROF_Q].apply(lambda x: x.profile),
            network[databases.Columns.PROF_A].apply(lambda x: x.profile),
            )
    else:
        network[databases.Columns.PSS] = network.apply(
            lambda x: x[databases.Columns.PROF_Q].calculate_pss(
                x[databases.Columns.PROF_A],
                method=method,
                ),
            axis=1,
        )
    return network

def pss(ar1, ar2):
    return sum(a == b for a, b in zip(ar1, ar2))

pss_vect = _np.vectorize(pss)