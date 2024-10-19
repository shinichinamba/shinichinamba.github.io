library(RefManageR)
library(readr)

get_bib <- function(title, doi, pmid) {
  tmp <- tempfile(fileext = ".bib")
  if (!missing(title)) {
    x <- RefManageR::ReadPubMed(title)
    WriteBib(x, tmp)
    Sys.sleep(5)
  } else if (!missing(doi)) {
    try(GetBibEntryWithDOI(doi, temp.file = tmp, delete.file = FALSE))
  } else if (!missing(pmid)) {
    x <- GetPubMedByID(pmid)
    WriteBib(x, tmp)
    Sys.sleep(10)
  } 
  res <- read_lines(tmp)
  unlink(tmp, force = TRUE)
  res
}
write_bib_texts <- function(..., out = stdout()) {
  write_lines(stringr::str_c(purrr::map_chr(list(...), stringr::str_c, collapse = "\n"), sep = "\n"), out)
} 

# write_bib_texts(
#   get_bib(doi = "10.1101/2021.11.18.21266545"), # GBMI PRS
#   get_bib(doi = "10.1101/2021.12.16.21267891"), # GBMI POAG
#   out = "_bibliography/preprints.bib"
# )

# write_bib_texts(
#   get_bib(doi = "10.1016/j.xgen.2022.100241"), # GBMI PRS
#   get_bib(doi = "10.1016/j.xgen.2022.100212"), # GBMI asthma
#   get_bib(doi = "10.1158/0008-5472.CAN-22-1492"), # cancer PRS & somatic alterations
#   get_bib(doi = "10.1016/j.xgen.2022.100192"), # GBMI flagship
#   get_bib(doi = "10.1016/j.xgen.2022.100190"), # GBMI drugdiscov
#   get_bib(title = "Stroke genetics informs drug discovery and risk prediction across ancestries"), # GIGASTROKE
#   get_bib(pmid = 36138222), # K Yamamoto assortative mating
#   get_bib(pmid = 35995775), # COVID19-eQTL
#   get_bib(pmid = 35940203), # COVID19-DOCK2
#   get_bib(pmid = 35753705), # ARD DrShirai
#   get_bib(pmid = 34906514), # {P}olygenic risk scores for prediction of breast cancer risk in {A}sian populations
#   get_bib(pmid = 34811492), # MuSTA
#   get_bib(pmid = 33310976), # Allelgy JPT review
#   get_bib(pmid = 30637877), # Methylation in cancer
#   out = "_bibliography/publications.bib"
# )
write_bib_texts(
  # get_bib(doi = "10.1126/sciadv.ade2780"),  # rs671
  # get_bib(doi = "10.1038/s41588-023-01500-0"),  # PRSadjGWAS
  # get_bib(doi = "10.1038/s41467-023-39136-7"),  # GSato PanCan
  # get_bib(doi = "10.1136/ard-2023-224537"),  # Tanaka 
  # get_bib(doi = "10.1038/s41467-023-41857-8"),  # Sekita
  # get_bib(doi = "10.1038/s41588-023-01375-1"),  # Edahiro scRNAseq
  # get_bib(doi = "10.1101/2023.03.31.23287839"), # Suzuki T2D Nature (preprint)
  # get_bib(doi = "10.1038/s41586-024-07019-6"), # Suzuki T2D Nature
  # get_bib(doi = "10.1016/j.xcrm.2024.101430"), # GBMI POAG
  # get_bib(doi = "10.1111/apt.17953"), # FIB4-EASL AP&T
  get_bib(doi = "10.15036/arerugi.72.1110"), # Arerugi WGS pipeline
  out = "_bibliography/tmp.bib"
)

write_bib_texts(
  get_bib(doi = "10.1038/s41588-024-01782-y"), # Ojima T2D PRS
  get_bib(doi = "10.1016/j.xgen.2024.100625"), # Tomofuji scLinax
  get_bib(doi = "10.1136/jnnp-2024-333690"), # Cris Kato
  get_bib(doi = "10.1038/s43856-024-00596-7"), # Naito causal forest
  get_bib(doi = "10.1038/s41588-024-01896-3"), # Wang TF e/pQTL
  get_bib(doi = "10.1038/s41562-024-02019-y") # Embryo PRS
)
write_bib_texts(get_bib(doi = "10.21203/rs.3.rs-4535534/v1")) # Ilana Caro prasma/CSF MR
