library(data.table)
library(parallel)
library(readODS)
library(readxl)

load_sessions_v1 <- function(idoc_folder) {
  sessions <- sort(list.files(idoc_folder, full.names = TRUE))
  return(
    list(
      pre = sessions[1],
      post = sessions[length(sessions)],
    )
  )
}

load_sessions_v2 <- function(idoc_folder) {
  sessions_file <- file.path(idoc_folder, "sessions.yaml")
  sessions <- yaml::read_yaml(sessions_file)
  # sessions$pre <- file.path(idoc_folder, sessions$pre)
  # pre_entry <- grep(pattern="pre", x=names(sessions), value=TRUE)[1]
  # sessions$pre <- file.path(idoc_folder, sessions[[pre_entry]])
  pre_entry <- tail(grep(pattern = "pre", x = names(sessions), value = TRUE), n = 1)

  sessions$pre <- file.path(idoc_folder, sessions[[pre_entry]])
  post_entry <- grep(pattern = "post", x = names(sessions), value = TRUE)[1]
  sessions$post <- file.path(idoc_folder, sessions[[post_entry]])

  return(sessions)
}

find_pi_file <- function(folder, test, idoc_folder, region_id, trial = NULL, verbose = FALSE, mm_decision_zone=7) {
  if (is.null(trial)) {
    pi_file <- list.files(folder, pattern = "_PI.csv", full.names = TRUE)
    if (length(pi_file) == 0) {
      pi_file <- list.files(folder, pattern = "GLOBAL_", mm_decision_zone, ".*mm.*csv", full.names = TRUE, recursive = TRUE)[1]
    }
  } else {
    result_folder <- file.path(folder, paste0(test, "_", trial, "_7mm"))
    if (!file.exists(result_folder)) {
      result_folder <- file.path(
        list.files(folder, pattern = paste0("& PI-DZ_", mm_decision_zone, "mm"), full.names = TRUE),
        paste0(test, "_", trial, "_7mm")
      )
    }
    pi_files <- list.files(result_folder, pattern = paste0(test, "_", trial, "_", mm_decision_zone, "mm.csv"), full.names = TRUE, recursive = TRUE)
    pi_files <- grep(pattern = "SUMMARY", x = pi_files, value = TRUE, invert = TRUE)
    pi_file <- pi_files
    # pi_file <- list.files(folder, pattern = paste0(test, "_", trial, "_7mm.csv"), full.names = TRUE, recursive=TRUE)
    if (length(pi_file) > 1) {
      stop(paste0("Multiple files found in ", folder))
    } # else if (length(pi_file) == 0) {
    #   warning(paste0("No files found in ", folder))
    # }
  }
  if (length(pi_file) == 0 || is.na(pi_file)) {
    if (verbose) warning(paste0("Cannot find ", test, " for ", idoc_folder, "_ROI_", region_id))
    return(NULL)
  }
  return(pi_file)
}

#' Read the Preference Index (PI) achieved by a fly in a trial or set of trials
#' Load the PI as computed by idocr (machine) and stored in a .csv file
#' The PI will be set to NA if only aversive or appetitive exits occur,
#' AND also if their sum is not at least min_exits
#' n_exits will be NA if only aversive or appetitive exits occur, otherwise it will be their sum
#' (even if under min_exits)
read_pi <- function(path, roi, min_exits = 3) {
  pis <- tryCatch(
    {
      dat <- data.table::as.data.table(read.csv(path))
      dat
    },
    warning = function(w) {
      warning(paste("Warning processing", path))
      dat <- data.table::fread(path)
      dat
    }
  )
  if ("apetitive" %in% colnames(pis)) {
    pis[, appetitive := apetitive]
    pis[, apetitive := NULL]
  }
  animal_data <- pis[region_id == roi, ]
  if (nrow(animal_data) == 0) {
    n_exits <- NA
    pi <- NA
  } else {
    n_exits <- animal_data$aversive + animal_data$appetitive
    if (is.na(n_exits)) {
      # n_exits <- NA
      pi <- NA
    } else if (n_exits < min_exits) {
      pi <- NA
    } else {
      pi <- animal_data[, preference_index]
    }
  }
  return(list(pi = pi, n_exits = n_exits, aversive = animal_data$aversive, appetitive = animal_data$appetitive))
}


average_trial <- function(results, min_exits_per_trial, use_incomplete_tests, use_global=FALSE) {
  n_na_trials <- sum(sapply(results, function(x) {
    is.na(x$pi)
  }))
  
  if (n_na_trials < 2) {

    pis <- sapply(results, function(x) {
      x$pi
    })
    pi <- mean(pis, na.rm = use_incomplete_tests)
    n_exits <- sum(sapply(results, function(x) {
      x$n_exits
    }), na.rm = use_incomplete_tests)
  } else if (use_global) {
    out <- combined_trial(results)
    n_exits <- out$n_exits
    pi <- out$pi
  } else {
    pi<- NA
    n_exits <- NA
  }

  return(list(pi = pi, n_exits = n_exits))
}

combined_trial <- function(results) {
  aversive <- sum(sapply(results, function(x) {
    ifelse(length(x$aversive) == 0, 0, x$aversive)
  }))
  appetitive <- sum(sapply(results, function(x) {
    ifelse(length(x$appetitive) == 0, 0, x$appetitive)
  }))
  n_exits <- aversive + appetitive
  pi <- (appetitive - aversive) / n_exits
  
  return(list(pi=pi, n_exits=n_exits))
}

best_trial <- function(results, min_exits_per_trial, use_incomplete_tests) {
  n_na_trials <- sum(sapply(results, function(x) {
    is.na(x$pi)
  }))

  if (n_na_trials < 2) {
    pis <- sapply(results, function(x) {
      x$pi
    })
    i <- which.min(pis)
    pi <- pis[i]
    n_exits <- sapply(results, function(x) {
      x$n_exits
    })[i]
  } else {
    out <- combined_trial(results)
    n_exits <- out$n_exits
    pi <- out$pi
  }

  if (!use_incomplete_tests & n_exits < min_exits_per_trial) {
    pi <- NA
  }

  return(list(pi = pi, n_exits = n_exits))
}

read_pi_multitrial <- function(session_folder, test, idoc_folder, region_id, trials, min_exits_per_trial = 3, verbose = FALSE, use_incomplete_tests = TRUE, summary_FUN = average_trial, mm_decision_zone = 7) {
  results <- lapply(trials, function(trial) {
    tryCatch(
      {
        val <- list(pi = NA, n_exits = NA, file = NA, aversive = NA, appetitive = NA, region_id=region_id)
        path <- find_pi_file(session_folder, test, idoc_folder, region_id, trial = trial, verbose = verbose, mm_decision_zone = mm_decision_zone)
        if (is.null(path)) {
          val
        } else {
          val <- read_pi(path, region_id, min_exits = min_exits_per_trial)
          val$file <- path
          val$region_id <- region_id
        }
        val
      },
      error = function(error) {
        if (verbose) warning(error)
        val
      }
    )
  })

  out <- summary_FUN[[test]](results, min_exits_per_trial = min_exits_per_trial, use_incomplete_tests = use_incomplete_tests)
  pi <- out$pi
  n_exits <- out$n_exits
  files <- sapply(results, function(x) {
    x$file
  })
  out <- list(pi = pi, n_exits = n_exits, files = files)

  if (!is.null(trials)) {
    for (trial in trials) {
      out[[paste0(test, "_", trial)]] <- results[[trial]]$pi
    }
  }
  return(out)
}

load_idoc_data <- function(metadata, ncores = 1, min_exits = 3, trials = 1:2, ...) {
  data <- do.call(rbind, parallel::mclapply(1:nrow(metadata), function(i) {
    meta <- metadata[i, ]
    sessions <- load_sessions_v2(meta$idoc_folder)
    for (test in c("PRE", "POST")) {
      region_id <- meta[[paste0(test, "_ROI")]]
      stopifnot(!is.null(region_id))
      val <- read_pi_multitrial(sessions[[tolower(test)]], test, meta$idoc_folder, region_id, trials = trials, min_exits_per_trial = min_exits, ...)
      meta[[test]] <- val$pi
      meta[[paste0(test, "_n_exits")]] <- val$n_exits
      meta[[paste0(test, "_files")]] <- list(val$files)
      for (trial in trials) {
        meta[[paste0(test, "_", trial, "_manual")]] <- meta[[paste0(test, "_", trial)]]
        meta[[paste0(test, "_", trial)]] <- val[[paste0(test, "_", trial)]]
      }
    }
    meta
  }, mc.cores = ncores))
  return(data)
}


read_idoc_metadata <- function(file, sheets, columns, backend = readxl::read_xlsx) {
  idoc_metadata <- lapply(
    sheets,
    function(sheet) {
      dt <- tryCatch(
        {
          dt <- as.data.table(suppressMessages(backend(file, sheet = sheet))[, columns])
          dt$sheet <- sheet
          dt$row_number <- 1:nrow(dt)
          dt$Files <- as.character(dt$Files)
          suppressWarnings(Files_formatted <- as.character(as.Date(as.integer(dt$Files), origin = "1899-12-30")))
          dt$Files[!is.na(Files_formatted)] <- Files_formatted[!is.na(Files_formatted)]
          dt$POST <- as.numeric(dt$POST)
          dt$PRE <- as.numeric(dt$PRE)

          # error if a fly does not have the Files annotation
          if (any(is.na(dt$Files))) {
            warning(paste0("Deleting ", paste(which(is.na(dt$Files)), collapse = " "), " rows from metadata"))
            dt <- dt[!is.na(Files), ]
          }
          dt
        },
        error = function(e) {
          print(e)
          print(sheet)
          NULL
        }
      )
    }
  )
  names(idoc_metadata) <- sheets
  metadata <- Reduce(x = idoc_metadata, f = function(x, y) {
    if (is.null(y)) {
      x
    } else if (nrow(y) == 0) {
      x
    } else if ("data.frame" %in% class(y)) {
      new_cols_y <- setdiff(colnames(y), colnames(x))
      new_cols_x <- setdiff(colnames(x), colnames(y))
      new_header <- unique(c(colnames(x), colnames(y)))

      for (col in new_cols_x) {
        y[[col]] <- NA
      }
      for (col in new_cols_y) {
        x[[col]] <- NA
      }
      rbind(x, y)
    } else {
      x
    }
  })
  return(metadata)
}
