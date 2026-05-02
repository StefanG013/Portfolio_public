# R/agent_api.R
# httr2 helper functions for communicating with the FastAPI trading agent backend.
# Base URL is read from the TRADING_API_URL env var (default: http://localhost:8000).

library(httr2)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

.api_base <- function() {
  url <- Sys.getenv("TRADING_API_URL", unset = "http://localhost:8000")
  sub("/$", "", url)  # strip trailing slash
}

.api_request <- function(path, ...) {
  request(paste0(.api_base(), path)) |>
    req_headers(`Accept` = "application/json") |>
    req_timeout(30)
}

.safe_perform <- function(req) {
  tryCatch(
    req_perform(req),
    error = function(e) {
      message("Trading API request failed: ", conditionMessage(e))
      NULL
    }
  )
}

# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

#' Fetch all transactions from the trading agent.
#'
#' @param limit Maximum number of rows to return (default 200).
#' @return A data.frame with transaction history, or NULL on failure.
get_transactions <- function(limit = 200) {
  resp <- .safe_perform(
    .api_request("/transactions") |>
      req_url_query(limit = limit)
  )
  if (is.null(resp)) return(NULL)
  tryCatch(
    as.data.frame(resp_body_json(resp, simplifyVector = TRUE)),
    error = function(e) {
      message("Failed to parse /transactions response: ", conditionMessage(e))
      NULL
    }
  )
}

#' Fetch transactions for a specific symbol.
#'
#' @param symbol Ticker symbol (e.g. "AAPL").
#' @param limit  Maximum number of rows to return.
#' @return A data.frame, or NULL if no data / on failure.
get_transactions_by_symbol <- function(symbol, limit = 200) {
  resp <- .safe_perform(
    .api_request(paste0("/transactions/", toupper(symbol))) |>
      req_url_query(limit = limit)
  )
  if (is.null(resp)) return(NULL)
  if (resp_status(resp) == 404) return(NULL)
  tryCatch(
    as.data.frame(resp_body_json(resp, simplifyVector = TRUE)),
    error = function(e) {
      message("Failed to parse /transactions/", symbol, " response: ", conditionMessage(e))
      NULL
    }
  )
}

# ---------------------------------------------------------------------------
# Agent control
# ---------------------------------------------------------------------------

#' Trigger the trading agent to run now.
#'
#' @return A list of result objects (one per symbol), or NULL on failure.
run_agent <- function() {
  resp <- .safe_perform(
    .api_request("/agent/run") |>
      req_method("POST") |>
      req_body_json(list())
  )
  if (is.null(resp)) return(NULL)
  tryCatch(
    resp_body_json(resp, simplifyVector = TRUE),
    error = function(e) {
      message("Failed to parse /agent/run response: ", conditionMessage(e))
      NULL
    }
  )
}

#' Get the current agent status (last run time, portfolio value, etc.).
#'
#' @return A named list, or NULL on failure.
get_agent_status <- function() {
  resp <- .safe_perform(.api_request("/agent/status"))
  if (is.null(resp)) return(NULL)
  tryCatch(
    resp_body_json(resp),
    error = function(e) {
      message("Failed to parse /agent/status response: ", conditionMessage(e))
      NULL
    }
  )
}

# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

#' Fetch current open positions from the Alpaca paper account.
#'
#' @return A data.frame of positions, or NULL on failure.
get_portfolio <- function() {
  resp <- .safe_perform(.api_request("/portfolio"))
  if (is.null(resp)) return(NULL)
  tryCatch(
    as.data.frame(resp_body_json(resp, simplifyVector = TRUE)),
    error = function(e) {
      message("Failed to parse /portfolio response: ", conditionMessage(e))
      NULL
    }
  )
}
