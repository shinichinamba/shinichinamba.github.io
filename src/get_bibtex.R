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
write_bib_texts <- function(..., out) {
  write_lines(stringr::str_c(purrr::map_chr(list(...), stringr::str_c, collapse = "\n"), sep = "\n"), out)
} 

write_bib_texts(
  get_bib(doi = "10.1101/2021.11.18.21266545"), # GBMI PRS
  get_bib(doi = "10.1101/2021.12.16.21267891"), # GBMI POAG
  out = "_bibliography/preprints.bib"
)

write_bib_texts(
  get_bib(doi = "10.1016/j.xgen.2022.100241"), # GBMI PRS
  get_bib(doi = "10.1016/j.xgen.2022.100212"), # GBMI asthma
  get_bib(doi = "10.1158/0008-5472.CAN-22-1492"), # cancer PRS & somatic alterations
  get_bib(doi = "10.1016/j.xgen.2022.100192"), # GBMI flagship
  get_bib(doi = "10.1016/j.xgen.2022.100190"), # GBMI drugdiscov
  get_bib(title = "Stroke genetics informs drug discovery and risk prediction across ancestries"), # GIGASTROKE
  get_bib(pmid = 36138222), # assortative mating
  get_bib(pmid = 35995775), # COVID19-eQTL
  get_bib(pmid = 35940203), # COVID19-DOCK2
  get_bib(pmid = 35753705), # ARD DrShirai
  get_bib(pmid = 34906514), # {P}olygenic risk scores for prediction of breast cancer risk in {A}sian populations
  get_bib(pmid = 34811492), # MuSTA
  get_bib(pmid = 33310976), # Allelgy JPT review
  get_bib(pmid = 30637877), # Methylation in cancer
  out = "_bibliography/publications.bib"
)

cat(get_bib(doi = "10.1016/j.xgen.2022.100241"), sep = "\n")
