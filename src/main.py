from cmu_graphics import *
import dataset
import models
import engine
import graphview
import ui

windowWidth, windowHeight = 1080, 700

margin = 16
headerHeight = 60
panelTop = headerHeight + margin
panelHeight = windowHeight - panelTop - margin

tableWidth = 250
resultsWidth = 280
graphWidth = windowWidth - 4 * margin - tableWidth - resultsWidth

tableLeft = margin
graphLeft = tableLeft + tableWidth + margin
resultsLeft = graphLeft + graphWidth + margin

backgroundColor = rgb(246, 246, 246)
markerColor = rgb(120, 120, 200)

sampleXs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
sampleYs = [2.4, 5.1, 6.2, 9.4, 10.1, 13.4, 14.0, 17.6, 18.1, 21.4, 22.2, 25.6]


def onAppStart(app):
    app.width, app.height = windowWidth, windowHeight

    app.data = dataset.Dataset()
    app.engine = engine.AnalysisEngine(app.data, models.makeAllModels())

    app.tablePanel = ui.Panel(tableLeft, panelTop, tableWidth, panelHeight,
                              'Data')
    app.graphPanel = ui.Panel(graphLeft, panelTop, graphWidth, panelHeight,
                              'Graph')
    app.resultsPanel = ui.Panel(resultsLeft, panelTop, resultsWidth,
                                panelHeight, 'Models')

    app.table = ui.DataTable(app.tablePanel)
    app.cards = ui.ModelCards(app.resultsPanel)

    # the scatterplot on top, the residual strip underneath it, sharing the
    # same left edge and width so the two line up column for column
    pad = 40
    graphHeight = app.graphPanel.contentHeight() - 200
    app.graph = graphview.GraphView(
        app.graphPanel.left + pad,
        app.graphPanel.contentTop() + 12,
        app.graphPanel.width - pad - 20,
        graphHeight)

    # the three tools take turns in one shared rectangle under the graph
    stripLeft = app.graph.left
    stripWidth = app.graph.width
    tabTop = app.graph.bottom + 30
    stripTop = tabTop + ui.TabBar.height
    stripHeight = 96

    app.tabs = ui.TabBar(stripLeft, tabTop, stripWidth,
                         [('Residuals', 'residuals'),
                          ('Predict', 'predict'),
                          ('Sensitivity', 'sensitivity')])
    app.mode = 'residuals'

    app.residuals = graphview.ResidualPlot(stripLeft, stripTop + 6,
                                           stripWidth, stripHeight - 12)
    app.predict = ui.PredictPanel(stripLeft, stripTop, stripWidth, stripHeight)
    app.sensitivity = ui.SensitivityPanel(stripLeft, stripTop, stripWidth,
                                          stripHeight)


    app.buttons = makeButtons()
    app.status = 'Click a cell in the table to start entering data.'
    refit(app)
    app.graph.fitToDataset(app.data)


def makeButtons():
    buttons = []
    left = margin
    for label, action, width in [('Sample', 'sample', 74),
                                 ('Undo', 'undo', 62),
                                 ('Include all', 'includeAll', 86),
                                 ('Clear', 'clear', 62)]:
        buttons.append(ui.Button(left, 30, width, 24, label, action))
        left += width + 6
    buttons.append(ui.Button(windowWidth - margin - 96, 20, 96, 24,
                             'Reframe graph', 'reframe'))
    return buttons


# every change to the data funnels through here. It re-runs the engine and
# deliberately leaves the graph window alone.
def refit(app):
    app.engine.analyze()


def loadSample(app):
    app.data = dataset.Dataset(list(sampleXs), list(sampleYs))
    app.engine = engine.AnalysisEngine(app.data, models.makeAllModels())
    app.table.cancelEdit()
    app.table.scrollTop = 0
    app.cards.expandedIndex = 0
    app.status = 'Loaded a sample dataset.'
    refit(app)
    # a whole new dataset is one of the two times reframing is wanted
    app.graph.fitToDataset(app.data)


def doAction(app, action):
    if action == 'sample':
        loadSample(app)
    elif action == 'undo':
        app.table.cancelEdit()
        app.status = 'Undo.' if app.data.undo() else 'Nothing to undo.'
        refit(app)
    elif action == 'includeAll':
        app.data.includeAll()
        app.status = 'All points included.'
        refit(app)
    elif action == 'clear':
        app.table.cancelEdit()
        app.data.clear()
        app.status = 'Cleared.'
        refit(app)
    elif action == 'reframe':
        app.graph.fitToDataset(app.data)
        app.status = 'Graph reframed.'


def onMousePress(app, mouseX, mouseY):
    for button in app.buttons:
        if button.contains(mouseX, mouseY):
            doAction(app, button.action)
            return

    if app.tablePanel.contains(mouseX, mouseY):
        # the table edits its own cells, but hands deletion and exclusion
        # back here so the controller stays in charge of the data
        request = app.table.handleClick(mouseX, mouseY, app.data)
        if request is not None:
            kind, row = request
            if kind == 'delete':
                app.data.deletePoint(row)
                app.status = f'Deleted row {row + 1}.'
            elif kind == 'mark':
                app.data.toggleExcluded(row)
                app.status = f'Toggled row {row + 1}.'
        refit(app)
        return

    if app.resultsPanel.contains(mouseX, mouseY):
        request = app.cards.handleClick(mouseX, mouseY, app.engine)
        if request is None:
            return
        kind, index = request
        result = app.engine.results[index]
        if kind == 'toggle':
            # the swatch controls whether this curve is on the graph
            result.isVisible = not result.isVisible
            app.status = f'{result.model.name} curve ' + \
                         ('shown.' if result.isVisible else 'hidden.')
        else:
            # clicking the open card closes it, so the panel can be collapsed
            if app.cards.expandedIndex == index:
                app.cards.expandedIndex = -1
                app.status = f'{result.model.name} collapsed.'
            else:
                app.cards.expandedIndex = index
                app.status = f'Showing residuals for {result.model.name}.'
        return

    if app.graph.isInPanel(mouseX, mouseY):
        if app.table.isEditing():
            app.table.commitCell(app.data)
            app.table.cancelEdit()
        x, y = app.graph.screenToData(mouseX, mouseY)
        if x is not None and y is not None:
            app.data.addPoint(x, y)
            app.status = 'Added a point by clicking the graph.'
            refit(app)


def onKeyPress(app, key):
    # while a cell is being edited the table gets first refusal on every key,
    # otherwise typing 'c' into a cell would clear the whole dataset
    if app.table.handleKey(key, app.data):
        refit(app)
        return

    if key == 'up':
        app.table.scrollBy(-1, app.data)
    elif key == 'down':
        app.table.scrollBy(1, app.data)
    elif key == 'f':
        doAction(app, 'reframe')
    elif key == 'u':
        doAction(app, 'undo')
    elif key == 's':
        doAction(app, 'sample')
    elif key in ('1', '2', '3', '4', '5', '6', '7'):
        index = int(key) - 1
        if index < len(app.engine.results):
            app.cards.expandedIndex = index
            app.status = ('Showing residuals for '
                          f'{app.engine.results[index].model.name}.')


def drawHeader(app):
    drawLabel('VeriFit!', margin, 14, size=18, bold=True, align='left')
    drawLabel('fitting data is not the same as predicting it',
              margin + 96, 16, size=11, align='left', fill=ui.mutedColor)
    for button in app.buttons:
        button.draw()


def drawGraphPanel(app):
    app.graphPanel.drawFrame()
    # a bug inside a view should not take the whole app down while the
    # interface is still being built
    try:
        app.graph.draw(app.data, app.engine)
        selected = app.cards.selectedResult(app.engine)
        if selected is None:
            app.residuals.drawEmpty('select a model to see its residuals')
        else:
            app.residuals.draw(selected, app.data.getRawXs(),
                               app.graph.xMin, app.graph.xMax,
                               selected.outlierIndex)
    except Exception as failure:
        drawLabel('a view raised:', app.graphPanel.left + 14,
                  app.graphPanel.contentTop() + 20, size=12, bold=True,
                  align='left', fill=ui.errorColor)
        drawLabel(f'{type(failure).__name__}: {failure}',
                  app.graphPanel.left + 14, app.graphPanel.contentTop() + 40,
                  size=10, align='left', fill=ui.errorColor)


def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill=backgroundColor)
    drawHeader(app)

    app.tablePanel.drawFrame()
    app.table.draw(app.data)

    drawGraphPanel(app)

    app.resultsPanel.drawFrame()
    app.cards.draw(app.engine, app.graph.colorFor, app.engine.tieMessage)

    offsetText = 'none'
    if app.data.usesOffset():
        offsetText = ui.formatCell(app.data.xOffset)
    drawLabel(f'{app.status}    x-offset: {offsetText}',
              margin, windowHeight - 8, size=10, align='left',
              fill=ui.mutedColor)


def main():
    runApp(width=windowWidth, height=windowHeight)


main()