#' Manually override scores with a human-made score
#' The manual score is provided in the PRE and POST columns of the metadata
#' and applied only if PRE_Reason and POST_reason have a reason other than empty, ? and Machine-override 
#' @export
update_scores_with_manual_annotation <- function(data, scoring_system) {
    data_raw[, PRE_machine := PRE]
    data_raw[, PRE_1_machine := PRE_1]
    data_raw[, PRE_2_machine := PRE_2]
    data_raw[, POST_machine := POST]
    data_raw[, POST_1_machine := POST_1]
    data_raw[, POST_2_machine := POST_2]
    
    
    if (scoring_system=="manual") {
      message("Using human made scores")   
      data_raw[, PRE := PRE_manual]
      data_raw[, POST := POST_manual]
      data_raw[, PRE_criteria := "manual"]
      data_raw[, POST_criteria := "manual"]
        
    } else if (scoring_system=="flexible") {
      message("Using flexible scores")   
      data_raw[, PRE := PRE_machine]
      data_raw[, POST := POST_machine]
      data_raw[, PRE_criteria := "machine"]
      data_raw[, POST_criteria := "machine"]
      data_raw[!is.na(PRE_manual) & !(PRE_Reason%in%c("", "?", "Machine-override")), PRE_criteria := "manual"]
      data_raw[!is.na(PRE_manual) & !(PRE_Reason%in%c("", "?", "Machine-override")), PRE := PRE_manual]
      data_raw[!is.na(POST_manual) & !(POST_Reason%in%c("", "?", "Machine-override")), POST_criteria := "manual"]
      data_raw[!is.na(POST_manual) & !(POST_Reason%in%c("", "?", "Machine-override")), POST := POST_manual]
        
    } else {
      message("Using machine made scores")   
      data_raw[ , PRE := PRE_machine]
      data_raw[ , POST := POST_machine]
    }
    return(data_raw)
}