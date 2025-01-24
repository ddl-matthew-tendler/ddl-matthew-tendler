# A Shiny app with URL-based navigation for specific drugs
library(shiny)

ui <- fluidPage(
  titlePanel("Drug-Specific Clinical Trial App"),
  sidebarLayout(
    sidebarPanel(
      selectInput("drug", "Select Drug:",
                  choices = c("a", "b", "c", "d"),
                  selected = "a"),
      sliderInput("sampleSize", "Sample Size", 
                  min = 10, max = 200, value = 50),
      numericInput("meanValue", "Mean (µ):", 0),
      numericInput("sdValue", "Std Dev (σ):", 1)
    ),
    mainPanel(
      plotOutput("distPlot"),
      br(),
      strong("Simulated Summary"),
      tableOutput("summaryTable")
    )
  )
)

server <- function(input, output, session) {
  # Handle query parameters
  observe({
    query <- parseQueryString(session$clientData$url_search)
    
    if (!is.null(query$drug)) {
      updateSelectInput(session, "drug", selected = query$drug)
    }
    if (!is.null(query$sampleSize)) {
      updateSliderInput(session, "sampleSize", value = as.numeric(query$sampleSize))
    }
    if (!is.null(query$meanValue)) {
      updateNumericInput(session, "meanValue", value = as.numeric(query$meanValue))
    }
    if (!is.null(query$sdValue)) {
      updateNumericInput(session, "sdValue", value = as.numeric(query$sdValue))
    }
  })
  
  # Update the URL when the drug selection changes
  observeEvent(input$drug, {
    updateQueryString(paste0("?drug=", input$drug), mode = "push")
  })
  
  # Reactive expression to simulate data based on user input
  simulatedData <- reactive({
    rnorm(input$sampleSize, mean = input$meanValue, sd = input$sdValue)
  })
  
  # Render plot
  output$distPlot <- renderPlot({
    hist(simulatedData(),
         main = paste("Distribution for Drug:", input$drug),
         xlab = "Simulated Values",
         col = "steelblue",
         border = "white")
  })
  
  # Render summary table
  output$summaryTable <- renderTable({
    data <- simulatedData()
    stats <- c(
      Min = round(min(data), 2),
      Q1 = round(quantile(data, 0.25), 2),
      Median = round(median(data), 2),
      Mean = round(mean(data), 2),
      Q3 = round(quantile(data, 0.75), 2),
      Max = round(max(data), 2)
    )
    as.data.frame(t(stats))
  }, rownames = TRUE)
}

# Run the Shiny App
shinyApp(ui, server)
