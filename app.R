# app.R — Portfolio Dashboard with AI Trading Agent
#
# Runs as a standard R Shiny app:
#   Rscript -e "shiny::runApp('app.R', port = 3838)"
#
# Requires packages: shiny, DT, ggplot2, plotly, httr2, scales
# Install with:
#   install.packages(c("shiny","DT","ggplot2","plotly","httr2","scales"))

library(shiny)
library(DT)
library(ggplot2)
library(plotly)

# Source the API helper functions
source("R/agent_api.R")

# ---------------------------------------------------------------------------
# Helper – read local CSV portfolio data
# ---------------------------------------------------------------------------

read_stocks <- function() {
  path <- "aandeel_stocks.csv"
  if (!file.exists(path)) return(data.frame())
  df <- tryCatch(
    read.csv(path, stringsAsFactors = FALSE, fileEncoding = "UTF-8-BOM"),
    error = function(e) read.csv(path, stringsAsFactors = FALSE)
  )
  df
}

read_crypto <- function() {
  path <- "aandeel_crypto.csv"
  if (!file.exists(path)) return(data.frame())
  df <- tryCatch(
    read.csv(path, stringsAsFactors = FALSE, fileEncoding = "UTF-8-BOM"),
    error = function(e) read.csv(path, stringsAsFactors = FALSE)
  )
  df
}

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

ui <- fluidPage(
  tags$head(
    tags$style(HTML("
      body { font-family: 'Segoe UI', sans-serif; background-color: #f5f7fa; }
      .navbar { background-color: #1a1a2e !important; }
      .navbar-brand, .navbar-nav > li > a { color: #e0e0e0 !important; }
      .value-box {
        background: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        text-align: center;
      }
      .value-box .value { font-size: 2em; font-weight: bold; color: #1a1a2e; }
      .value-box .label { color: #666; font-size: 0.9em; margin-top: 4px; }
      .status-indicator {
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        margin-right: 6px;
      }
      .status-online  { background-color: #28a745; }
      .status-offline { background-color: #dc3545; }
      .card {
        background: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
      }
    "))
  ),

  navbarPage(
    title = "📈 Portfolio Dashboard",
    id    = "main_nav",
    theme = NULL,

    # -----------------------------------------------------------------------
    # Tab 1 – My Portfolio
    # -----------------------------------------------------------------------
    tabPanel(
      "My Portfolio",
      br(),
      fluidRow(
        column(12,
          div(class = "card",
            h3("📊 Stocks"),
            DTOutput("tbl_stocks")
          )
        )
      ),
      fluidRow(
        column(12,
          div(class = "card",
            h3("₿ Crypto"),
            DTOutput("tbl_crypto")
          )
        )
      )
    ),

    # -----------------------------------------------------------------------
    # Tab 2 – AI Agent
    # -----------------------------------------------------------------------
    tabPanel(
      "🤖 AI Agent",
      br(),

      # Status row
      fluidRow(
        column(4,
          div(class = "value-box",
            uiOutput("ui_agent_status_dot"),
            div(class = "value", uiOutput("ui_portfolio_value")),
            div(class = "label", "Portfolio Value (Paper)")
          )
        ),
        column(4,
          div(class = "value-box",
            div(class = "value", uiOutput("ui_cash_value")),
            div(class = "label", "Available Cash")
          )
        ),
        column(4,
          div(class = "value-box",
            div(class = "value", uiOutput("ui_last_run")),
            div(class = "label", "Last Agent Run (UTC)")
          )
        )
      ),

      # Control row
      fluidRow(
        column(12,
          div(class = "card",
            fluidRow(
              column(6,
                h4("Agent Control"),
                actionButton(
                  "btn_run_agent",
                  "▶ Run Agent Now",
                  class = "btn btn-primary btn-lg"
                ),
                span(style = "margin-left:15px; color: #666;",
                  "Auto-refreshes every 30 seconds"
                )
              ),
              column(6,
                h4("Last Run Results"),
                verbatimTextOutput("txt_run_results")
              )
            )
          )
        )
      ),

      # Transactions table
      fluidRow(
        column(12,
          div(class = "card",
            h4("📋 Transaction History"),
            DTOutput("tbl_transactions")
          )
        )
      ),

      # P&L chart
      fluidRow(
        column(12,
          div(class = "card",
            h4("📈 Executed Trades P&L"),
            plotlyOutput("plot_pnl", height = "350px")
          )
        )
      ),

      # Open positions
      fluidRow(
        column(12,
          div(class = "card",
            h4("💼 Current Open Positions"),
            DTOutput("tbl_positions")
          )
        )
      )
    )
  )
)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

server <- function(input, output, session) {

  # Auto-refresh timer (every 30 seconds)
  auto_timer <- reactiveTimer(30000)

  # -------------------------------------------------------------------------
  # Portfolio tab
  # -------------------------------------------------------------------------

  output$tbl_stocks <- renderDT({
    df <- read_stocks()
    if (nrow(df) == 0) return(datatable(data.frame(Message = "No data found")))
    datatable(df,
      options = list(pageLength = 25, scrollX = TRUE),
      rownames = FALSE,
      class    = "stripe hover"
    )
  })

  output$tbl_crypto <- renderDT({
    df <- read_crypto()
    if (nrow(df) == 0) return(datatable(data.frame(Message = "No data found")))
    datatable(df,
      options = list(pageLength = 25, scrollX = TRUE),
      rownames = FALSE,
      class    = "stripe hover"
    )
  })

  # -------------------------------------------------------------------------
  # AI Agent tab – reactive data sources
  # -------------------------------------------------------------------------

  # Status (refreshes on timer or on demand)
  agent_status <- reactive({
    auto_timer()
    get_agent_status()
  })

  # Transactions (refreshes on timer or after a run)
  transactions_rv <- reactiveVal(NULL)

  observe({
    auto_timer()
    transactions_rv(get_transactions(limit = 500))
  })

  # -------------------------------------------------------------------------
  # Status cards
  # -------------------------------------------------------------------------

  output$ui_agent_status_dot <- renderUI({
    status <- agent_status()
    if (!is.null(status)) {
      tags$span(
        tags$span(class = "status-indicator status-online"),
        "API Online"
      )
    } else {
      tags$span(
        tags$span(class = "status-indicator status-offline"),
        "API Offline"
      )
    }
  })

  output$ui_portfolio_value <- renderUI({
    status <- agent_status()
    val <- if (!is.null(status)) status$portfolio_value else NA
    if (is.null(val) || is.na(val)) return(HTML("&mdash;"))
    HTML(paste0("$", formatC(val, format = "f", digits = 2, big.mark = ",")))
  })

  output$ui_cash_value <- renderUI({
    status <- agent_status()
    val <- if (!is.null(status)) status$cash else NA
    if (is.null(val) || is.na(val)) return(HTML("&mdash;"))
    HTML(paste0("$", formatC(val, format = "f", digits = 2, big.mark = ",")))
  })

  output$ui_last_run <- renderUI({
    status <- agent_status()
    lr <- if (!is.null(status)) status$last_run else NULL
    if (is.null(lr)) return(HTML("Never"))
    # Format: "2024-01-15 14:30:00"
    HTML(format(as.POSIXct(lr, format = "%Y-%m-%dT%H:%M:%OS", tz = "UTC"),
                "%Y-%m-%d %H:%M"))
  })

  # -------------------------------------------------------------------------
  # Run agent button
  # -------------------------------------------------------------------------

  run_results_rv <- reactiveVal("Press 'Run Agent Now' to trigger the agent.")

  observeEvent(input$btn_run_agent, {
    run_results_rv("⏳ Running agent — please wait...")
    results <- run_agent()
    if (is.null(results)) {
      run_results_rv("❌ Could not reach the trading API. Is it running?")
      return()
    }

    # Refresh transactions immediately
    transactions_rv(get_transactions(limit = 500))

    if (length(results) == 0) {
      run_results_rv("Agent ran but returned no results.")
      return()
    }

    lines <- vapply(results, function(r) {
      sprintf("[%s] %s → %s (%s)",
              r$symbol, r$action, r$status,
              if (!is.null(r$reasoning)) substr(r$reasoning, 1, 80) else "")
    }, character(1))
    run_results_rv(paste(lines, collapse = "\n"))
  })

  output$txt_run_results <- renderText({
    run_results_rv()
  })

  # -------------------------------------------------------------------------
  # Transactions table
  # -------------------------------------------------------------------------

  output$tbl_transactions <- renderDT({
    df <- transactions_rv()
    if (is.null(df) || nrow(df) == 0) {
      return(datatable(
        data.frame(Message = "No transactions yet. Press 'Run Agent Now' or wait for the scheduler."),
        options = list(dom = "t"), rownames = FALSE
      ))
    }

    # Colour-code the Action column
    datatable(df,
      options  = list(pageLength = 15, scrollX = TRUE, order = list(list(0, "desc"))),
      rownames = FALSE,
      class    = "stripe hover compact"
    ) |>
      formatStyle(
        "action",
        backgroundColor = styleEqual(
          c("BUY",  "SELL", "HOLD"),
          c("#d4edda", "#f8d7da", "#fff3cd")
        )
      ) |>
      formatStyle(
        "status",
        color = styleEqual(
          c("EXECUTED", "DRY_RUN", "FAILED", "SKIPPED"),
          c("#155724",  "#0c5460",  "#721c24", "#856404")
        ),
        fontWeight = "bold"
      )
  })

  # -------------------------------------------------------------------------
  # P&L chart
  # -------------------------------------------------------------------------

  output$plot_pnl <- renderPlotly({
    df <- transactions_rv()

    empty_plot <- plot_ly() |>
      layout(
        title = "No executed trade data yet",
        xaxis = list(title = ""),
        yaxis = list(title = "P&L ($)")
      )

    if (is.null(df) || nrow(df) == 0) return(empty_plot)

    pnl_df <- df[!is.na(df$pnl) & df$action %in% c("BUY", "SELL"), ]
    if (nrow(pnl_df) == 0) return(empty_plot)

    pnl_df$timestamp <- as.POSIXct(pnl_df$timestamp, format = "%Y-%m-%dT%H:%M:%OS", tz = "UTC")
    pnl_df <- pnl_df[order(pnl_df$timestamp), ]
    pnl_df$cumulative_pnl <- cumsum(ifelse(is.na(pnl_df$pnl), 0, pnl_df$pnl))

    plot_ly(pnl_df, x = ~timestamp, y = ~cumulative_pnl,
            type = "scatter", mode = "lines+markers",
            line = list(color = "#1a1a2e"),
            marker = list(color = ifelse(pnl_df$pnl >= 0, "#28a745", "#dc3545"), size = 8),
            text = ~paste0(symbol, " ", action, "<br>P&L: $", round(pnl, 2)),
            hoverinfo = "text+x+y") |>
      layout(
        xaxis = list(title = "Date"),
        yaxis = list(title = "Cumulative P&L ($)"),
        showlegend = FALSE
      )
  })

  # -------------------------------------------------------------------------
  # Open positions
  # -------------------------------------------------------------------------

  output$tbl_positions <- renderDT({
    auto_timer()
    pos <- get_portfolio()

    if (is.null(pos) || nrow(pos) == 0) {
      return(datatable(
        data.frame(Message = "No open positions (API offline or no positions held)"),
        options = list(dom = "t"), rownames = FALSE
      ))
    }

    datatable(pos,
      options = list(pageLength = 10, scrollX = TRUE),
      rownames = FALSE,
      class    = "stripe hover"
    ) |>
      formatStyle(
        "unrealized_pl",
        color = styleInterval(0, c("#dc3545", "#28a745")),
        fontWeight = "bold"
      )
  })
}

# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

shinyApp(ui = ui, server = server)
