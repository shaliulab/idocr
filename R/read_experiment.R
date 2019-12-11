#' Read experiment data (odors and lemdt_results csv)
#' @importFrom data.table fread
#' @export
read_experiment <- function(self) {
  
  experiment_folder <- self$experiment_folder
  # read odors
  odors_csv <- file.path(experiment_folder, 'odors.csv')
  if (file.exists(odors_csv)) {
    odors_table <- fread(odors_csv, sep = ',', header=T, stringsAsFactors = F)
    if(is.null(A)) A <- odors_table$odor_A
    if(is.null(B)) B <- odors_table$odor_B
  } else {
    if(is.null(A)) A <- "A"
    if(is.null(B)) B <- "B"
  }
  
  self$A <- A
  self$B <- B
  self$odours <- c(A, B)
  names(self$colours) <- self$odours 
  
  # read experiment data
  filename <- list.files(path = experiment_folder, pattern = 'LeMDT') %>% grep(pattern = '.csv', x = ., value = T)
  file_path <- file.path(experiment_folder, filename)
  if (length(file_path) == 0) {
    stop('Provided path to trace file does not exist')
    return(1)
  }
  
  # read the data
  lemdt_result <- fread(file = file_path, sep = ',', header = T, stringsAsFactors = F)
  # discard rows with NA 
  lemdt_result <- na.omit(lemdt_result)
  # discard the first column, it has the count of rows up to the filled cache (not needed here)
  lemdt_result <- lemdt_result[,-1]
  # keep only the selected flies
  lemdt_result <- lemdt_result[arena %in% c(0, self$selected_flies),]
  # bind the data to self 
  self$lemdt_result <- lemdt_result
  
  # read paradigm
  self$paradigm <- fread(file = file.path(self$experiment_folder, 'paradigm.csv'))
  
  return(self)
}