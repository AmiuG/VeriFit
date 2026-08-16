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

backgroundColor = rgb(244, 246, 249)
markerColor = rgb(120, 120, 200)


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
                          ('Sensitivity', 'sensitivity'),
                          ('Influence', 'influence'),
                          ('R2 vs CV', 'rsquared')])
    app.mode = 'residuals'

    app.influence = None

    # the residual box starts flush against the tabs, so the two read as
    # one tabbed panel instead of two floating rectangles
    app.residuals = graphview.ResidualPlot(stripLeft, stripTop,
                                           stripWidth, stripHeight)
    app.predict = ui.PredictPanel(stripLeft, stripTop + 6, stripWidth,
                                  stripHeight)
    app.sensitivity = ui.SensitivityPanel(stripLeft, stripTop + 6, stripWidth,
                                          stripHeight)
    app.influencePanel = ui.InfluencePanel(stripLeft, stripTop + 6, stripWidth,
                                           stripHeight)
    app.rsquaredPanel = ui.RSquaredPanel(stripLeft, stripTop + 6, stripWidth,
                                         stripHeight)

    app.buttons = makeButtons()
    # the Sample dropdown sits just left of the ? button
    app.samples = ui.SampleMenu(windowWidth - margin - 96 - 34 - 70, 20)
    app.pressedButton = None
    # where the mouse is resting, so buttons can light up under it
    app.mouseX, app.mouseY = -1, -1
    app.windowControls = ui.WindowControls(app.graphPanel)
    app.help = ui.HelpOverlay(windowWidth, windowHeight)
    app.status = 'Click a cell in the table to start entering data.'
    app.sampleIndex = -1
    refit(app)
    app.graph.fitToDataset(app.data)


def makeButtons():
    buttons = []
    left = margin
    for label, action, width in [('Undo', 'undo', 62),
                                 ('Include all', 'includeAll', 86),
                                 ('Clear', 'clear', 62)]:
        buttons.append(ui.Button(left, 30, width, 24, label, action))
        left += width + 6
    buttons.append(ui.Button(windowWidth - margin - 96, 20, 96, 24,
                             'Reframe graph', 'reframe'))
    buttons.append(ui.Button(windowWidth - margin - 96 - 34, 20, 28, 24,
                             '?', 'help'))
    return buttons


# every change to the data funnels through here. It re-runs the engine and
# deliberately leaves the graph window alone.
def refit(app):
    # remember which model's card is open, because ranks may shuffle
    expandedName = app.cards.selectedName(app.engine)
    app.engine.analyze()
    app.cards.reselect(app.engine, expandedName)

    app.influence = None
    if app.mode == 'influence':
        refreshInfluence(app)

def refreshInfluence(app):
    app.influence = app.engine.influenceSweep()

def selected(app):
    return app.cards.selectedResult(app.engine)

def loadSample(app, index):
    label, hint, xs, ys = dataset.samples[index]
    app.sampleIndex = index
    app.data = dataset.Dataset(list(xs), list(ys))
    app.engine = engine.AnalysisEngine(app.data, models.makeAllModels())
    app.table.cancelEdit()
    app.table.scrollTop = 0
    app.cards.expandedIndex = 0
    app.status = f'{label} sample: {hint}'
    refit(app)
    # a whole new dataset is one of the two times reframing is wanted
    app.graph.fitToDataset(app.data)


def doAction(app, action):
    if action == 'undo':
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
    elif action == 'help':
        app.help.isOpen = True
        app.status = 'Help.'
    elif action == 'resetParams':
        # refitting is the honest way back: it restores the parameters and
        # clears isAdjusted, so CV and AICc become meaningful again
        refit(app)
        app.status = 'Parameters reset to the fitted values.'


def onMousePress(app, mouseX, mouseY):
    # while the help overlay is up, any click just dismisses it
    if app.help.isOpen:
        app.help.isOpen = False
        return
    request = app.samples.handleClick(mouseX, mouseY)
    if request is not None:
        if request.startswith('sample'):
            loadSample(app, int(request[len('sample'):]))
        elif app.samples.isOpen:
            app.status = 'Pick a sample dataset.'
        return
    if app.windowControls.handleClick(mouseX, mouseY, app.graph):
        app.status = 'Editing the graph window.'
        return
    for button in app.buttons:
        if button.contains(mouseX, mouseY):
            app.pressedButton = button
            doAction(app, button.action)
            return
        
    tabKey = app.tabs.keyAt(mouseX, mouseY)
    if tabKey is not None:
        app.mode = tabKey
        if tabKey == 'influence' and app.influence is None:
            refreshInfluence(app)
        app.sensitivity.draggingIndex = None
        app.predict.isEditing = False
        app.status = f'Showing {tabKey}.'
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
        if app.cards.verdictButton.contains(mouseX, mouseY):
            app.cards.showVerdict = not app.cards.showVerdict
            app.status = ('Verdict shown.' if app.cards.showVerdict
                          else 'Verdict hidden.')
            return
        request = app.cards.handleClick(mouseX, mouseY, app.engine)
        if request is None:
            return
        kind, index = request
        result = app.engine.results[index]
        if kind == 'toggle':
            # the swatch controls whether this curve is on the graph
            app.engine.setVisible(result, not result.isVisible)
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

    if app.mode == 'predict':
        if app.predict.handleClick(mouseX, mouseY):
            return
    elif app.mode == 'sensitivity':
        if app.sensitivity.resetButton.contains(mouseX, mouseY):
            doAction(app, 'resetParams')
            return
        index = app.sensitivity.sliderAt(mouseX, mouseY, selected(app))
        if index is not None:
            app.sensitivity.draggingIndex = index
            dragSlider(app, mouseX)
            return

    if app.graph.isInPanel(mouseX, mouseY):
        # in predict mode a click on the graph moves the marker instead of
        # adding a point, otherwise you could never place it precisely
        if app.mode == 'predict':
            x, y = app.graph.screenToData(mouseX, mouseY)
            app.predict.setValue(x)
            app.status = 'Prediction marker moved.'
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

def dragSlider(app, mouseX):
    result = selected(app)
    params = app.sensitivity.valueFromDrag(mouseX, result)
    if params is None:
        return
    result.model.setParams(params)
    # the residual plot and the card numbers follow the slider live
    app.engine.rescoreAdjusted(result)
    app.status = f'{result.model.name} adjusted by hand.'


def onMouseDrag(app, mouseX, mouseY):
    if app.mode == 'sensitivity' and app.sensitivity.draggingIndex is not None:
        dragSlider(app, mouseX)
    elif app.mode == 'predict' and app.graph.isInPanel(mouseX, mouseY):
        x, y = app.graph.screenToData(mouseX, mouseY)
        app.predict.setValue(x)


def onMouseMove(app, mouseX, mouseY):
    app.mouseX, app.mouseY = mouseX, mouseY


def onMouseRelease(app, mouseX, mouseY):
    app.sensitivity.draggingIndex = None
    app.pressedButton = None


def onKeyPress(app, key):
    if app.help.isOpen:
        app.help.isOpen = False
        return
    if app.windowControls.handleKey(key, app.graph):
        return

    if app.mode == 'predict' and app.predict.handleKey(key):
        return
    # while a cell is being edited the table gets first refusal on every key,
    # otherwise typing 'c' into a cell would clear the whole dataset
    if app.table.handleKey(key, app.data):
        refit(app)
        return

    # arrows pan the graph, except while a cell is being edited, when
    # up and down keep scrolling the table
    if app.table.isEditing() and key in ('up', 'down', 'left', 'right'):
        if key == 'up':
            app.table.scrollBy(-1, app.data)
        elif key == 'down':
            app.table.scrollBy(1, app.data)
    elif key == 'up':
        app.graph.pan(0, 0.1)
    elif key == 'down':
        app.graph.pan(0, -0.1)
    elif key == 'left':
        app.graph.pan(-0.1, 0)
    elif key == 'right':
        app.graph.pan(0.1, 0)
    elif key in ('=', '+'):
        app.graph.zoom(0.8)
    elif key in ('-', '_'):
        app.graph.zoom(1.25)
    elif key == 'f':
        doAction(app, 'reframe')
    elif key == 'u':
        doAction(app, 'undo')
    elif key == 's':
        # each press moves on to the next sample, like a little tour
        loadSample(app, (app.sampleIndex + 1) % len(dataset.samples))
    elif key == 'r':
        app.mode = 'residuals'
    elif key == 'p':
        app.mode = 'predict'
    elif key == 'v':
        app.mode = 'sensitivity'
    elif key in ('1', '2', '3', '4', '5', '6', '7'):
        index = int(key) - 1
        if index < len(app.engine.results):
            app.cards.expandedIndex = index
            app.status = ('Showing residuals for '
                          f'{app.engine.results[index].model.name}.')
    elif key == 'i':
        app.mode = 'influence'
        if app.influence is None:
            refreshInfluence(app)
    elif key == 'q':
        app.mode = 'rsquared'
    elif key == 'h':
        app.help.isOpen = True


def drawHeader(app):
    # a white band anchors the header instead of floating on the gray
    drawRect(0, 0, windowWidth, headerHeight, fill='white')
    drawLine(0, headerHeight, windowWidth, headerHeight,
             fill=ui.panelBorder, lineWidth=1)
    # the exclamation mark carries the accent color, and is the only part
    # of the title that is not near black. The name ends exactly where the
    # mark begins, so the two always meet however wide the font renders.
    # the name is measured at 71px wide, so ending it here leaves the V
    # sitting flush above the Undo button
    joinX = margin + 71
    drawLabel('VeriFit', joinX, 16, size=22, bold=True, align='right',
              fill=rgb(25, 30, 38), font=ui.titleFont)
    drawLabel('!', joinX + 2, 16, size=22, bold=True, align='left',
              fill=ui.accentColor, font=ui.titleFont)
    drawLabel('fitting data is not the same as predicting it',
              joinX + 26, 18, size=11, align='left', italic=True,
              fill=ui.mutedColor, font=ui.bodyFont)
    for button in app.buttons:
        button.draw(pressed=(button is app.pressedButton),
                    hovered=button.contains(app.mouseX, app.mouseY))
    app.samples.drawButton(app.mouseX, app.mouseY)


def drawStrip(app):
    result = selected(app)
    if app.mode == 'residuals':
        if result is None:
            app.residuals.drawEmpty('select a model to see its residuals')
        else:
            app.residuals.draw(result, app.data.getRawXs(),
                               app.graph.xMin, app.graph.xMax,
                               result.outlierIndex)
    elif app.mode == 'predict':
        app.predict.draw(app.data, app.engine, result, app.graph.colorFor)
    elif app.mode == 'sensitivity':
        app.sensitivity.draw(result)
    elif app.mode == 'influence':
        app.influencePanel.draw(app.influence, app.data,
                                app.graph.xMin, app.graph.xMax)
    else:
        app.rsquaredPanel.draw(app.engine, app.graph.colorFor)


def drawGraphPanel(app):
    app.graphPanel.drawFrame()
    # a bug inside a view should not take the whole app down while the
    # interface is still being built
    try:
        app.graph.draw(app.data, app.engine)
        result = selected(app)
        # the selected model also shows its plausible range
        if result is not None and result.isVisible:
            app.graph.drawBand(app.engine, result, app.graph.colorFor(result))
        # the untouched fit stays visible behind a hand-adjusted curve
        if result is not None and result.isAdjusted():
            app.graph.drawGhostCurve(app.engine, result,
                                     app.graph.colorFor(result))
        if app.mode == 'predict' and app.predict.value is not None:
            app.graph.drawPredictionMarker(app.engine, app.predict.value,
                                           markerColor)
        app.tabs.draw(app.mode, app.tabs.keyAt(app.mouseX, app.mouseY))
        drawStrip(app)
        app.windowControls.draw(app.graph, app.mouseX, app.mouseY)
    except Exception as failure:
        drawLabel('a view raised:', app.graphPanel.left + 14,
                  app.graphPanel.contentTop() + 20, size=12, bold=True,
                  align='left', fill=ui.errorColor, font=ui.bodyFont)
        drawLabel(f'{type(failure).__name__}: {failure}',
                  app.graphPanel.left + 14, app.graphPanel.contentTop() + 40,
                  size=10, align='left', fill=ui.errorColor, font=ui.bodyFont)


def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill=backgroundColor)
    drawHeader(app)

    app.tablePanel.drawFrame()
    app.table.draw(app.data)

    drawGraphPanel(app)

    app.resultsPanel.drawFrame()
    app.cards.draw(app.engine, app.graph.colorFor, app.mouseX, app.mouseY)

    offsetText = 'none'
    if app.data.usesOffset():
        offsetText = ui.formatCell(app.data.xOffset)
    # a slim white band keeps the status line from getting lost
    drawRect(0, windowHeight - margin, windowWidth, margin, fill='white')
    drawLine(0, windowHeight - margin, windowWidth, windowHeight - margin,
             fill=ui.panelBorder, lineWidth=1)
    drawLabel(f'{app.status}    x-offset: {offsetText}',
              margin, windowHeight - margin / 2, size=10, align='left',
              fill=ui.mutedColor, font=ui.bodyFont)

    # the open sample menu and the overlay go on last, above the panels
    app.samples.drawMenu(app.sampleIndex, app.mouseX, app.mouseY)
    app.help.draw()


def main():
    runApp(width=windowWidth, height=windowHeight)


main()