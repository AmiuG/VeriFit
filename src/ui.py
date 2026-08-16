from cmu_graphics import *
import dataset

panelFill = rgb(255, 255, 255)
panelBorder = rgb(205, 205, 205)
# the one accent color, used sparingly so it always means "look here"
accentColor = rgb(0, 114, 178)
accentPressed = rgb(0, 90, 145)
titleFill = rgb(242, 242, 242)
textColor = 'black'
mutedColor = rgb(125, 125, 125)
errorColor = rgb(200, 40, 40)
selectFill = rgb(219, 234, 254)
editFill = rgb(254, 243, 199)
buttonFill = rgb(248, 248, 248)
buttonDown = rgb(226, 226, 226)
tabActiveFill = rgb(255, 255, 255)
tabIdleFill = rgb(236, 236, 236)
sliderTrack = rgb(220, 220, 220)
sliderKnob = rgb(70, 70, 70)
warningFill = rgb(255, 244, 214)
influenceBarColor = rgb(150, 150, 150)
influenceAlertColor = rgb(200, 40, 40)
slopeLineColor = rgb(190, 190, 190)


# 3.0 -> '3', 2.5 -> '2.5', 1/3 -> '0.3333'
def formatCell(value):
    # a tiny value would come out as '0.0000', so show it like 4e-05 instead
    if value != 0 and abs(value) < 0.001:
        return f'{value:.4g}'
    text = f'{value:.4f}'
    number = float(text)
    if number == int(number):
        return str(int(number))
    return text.rstrip('0').rstrip('.')


class Panel:
    titleHeight = 26

    def __init__(self, left, top, width, height, title):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.right, self.bottom = left + width, top + height
        self.title = title

    # where a panel's contents may start drawing
    def contentTop(self):
        return self.top + Panel.titleHeight

    def contentHeight(self):
        return self.height - Panel.titleHeight

    def contains(self, mouseX, mouseY):
        return (self.left <= mouseX <= self.right and
                self.top <= mouseY <= self.bottom)

    def drawFrame(self):
        drawRect(self.left, self.top, self.width, self.height, fill=panelFill)
        drawRect(self.left, self.top, self.width, Panel.titleHeight, fill=titleFill)
        drawLabel(self.title, self.left + 10, self.top + Panel.titleHeight / 2,
                  size=12, bold=True, align='left', fill=textColor)
        drawRect(self.left, self.top, self.width, self.height,
                 fill=None, border=panelBorder)


class Button:
    def __init__(self, left, top, width, height, label, action):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.label = label
        # a plain string that main.py switches on, so ui.py stays ignorant
        # of what the button actually does
        self.action = action

    def contains(self, mouseX, mouseY):
        return (self.left <= mouseX <= self.left + self.width and
                self.top <= mouseY <= self.top + self.height)

    def draw(self, enabled = True, pressed = False, primary = False):
        # a primary button is filled with the accent color, so the one
        # action a new user needs stands out from the gray ones
        if primary:
            drawRect(self.left, self.top, self.width, self.height,
                     fill=accentPressed if pressed else accentColor)
            drawLabel(self.label, self.left + self.width / 2,
                      self.top + self.height / 2, size=11, bold=True,
                      fill='white')
            return
        fill = buttonDown if pressed else buttonFill
        drawRect(self.left, self.top, self.width, self.height,
                 fill=fill, border=panelBorder)
        drawLabel(self.label, self.left + self.width / 2,
                  self.top + self.height / 2, size=11,
                  fill=textColor if enabled else mutedColor)

class TabBar:
    height = 22

    def __init__(self, left, top, width, tabs):
        # tabs is a list of (label, key); the key is what main.py switches on
        self.left, self.top, self.width = left, top, width
        self.tabs = tabs
        self.tabWidth = width / len(tabs)

    def keyAt(self, mouseX, mouseY):
        if not (self.top <= mouseY <= self.top + TabBar.height):
            return None
        if not (self.left <= mouseX <= self.left + self.width):
            return None
        index = int((mouseX - self.left) // self.tabWidth)
        if index < 0 or index >= len(self.tabs):
            return None
        return self.tabs[index][1]

    def draw(self, activeKey):
        for i in range(len(self.tabs)):
            label, key = self.tabs[i]
            left = self.left + i * self.tabWidth
            isActive = (key == activeKey)
            drawRect(left, self.top, self.tabWidth, TabBar.height,
                     fill=tabActiveFill if isActive else tabIdleFill,
                     border=panelBorder)
            drawLabel(label, left + self.tabWidth / 2,
                      self.top + TabBar.height / 2, size=11,
                      bold=isActive, fill=textColor if isActive else mutedColor)

class Slider:
    trackHeight = 4
    knobRadius = 6
    labelWidth = 74

    def __init__(self, left, top, width):
        self.left, self.top, self.width = left, top, width
        self.trackLeft = left + Slider.labelWidth
        self.trackWidth = width - Slider.labelWidth - 74

    # where the knob sits for a value inside (low, high)
    def knobX(self, value, low, high):
        if high <= low:
            return self.trackLeft + self.trackWidth / 2
        fraction = (value - low) / (high - low)
        fraction = min(1, max(0, fraction))
        return self.trackLeft + fraction * self.trackWidth

    # the value a mouse position corresponds to, clamped to the range
    def valueAt(self, mouseX, low, high):
        if self.trackWidth <= 0:
            return low
        fraction = (mouseX - self.trackLeft) / self.trackWidth
        fraction = min(1, max(0, fraction))
        return low + fraction * (high - low)

    def contains(self, mouseX, mouseY):
        return (self.left <= mouseX <= self.left + self.width and
                abs(mouseY - self.top) <= Slider.knobRadius + 4)

    def draw(self, name, value, low, high, isAdjusted):
        drawLabel(name, self.left, self.top, size=10, align='left',
                  fill=textColor)
        drawRect(self.trackLeft, self.top - Slider.trackHeight / 2,
                 self.trackWidth, Slider.trackHeight, fill=sliderTrack)
        drawCircle(self.knobX(value, low, high), self.top, Slider.knobRadius,
                   fill=errorColor if isAdjusted else sliderKnob)
        drawLabel(formatScore(value, 4), self.left + self.width, self.top,
                  size=10, align='right', fill=mutedColor)

# ----------------------------------------------------------------------
# THE DATA TABLE
# ----------------------------------------------------------------------
class DataTable:
    rowHeight = 21 # each data row height
    headerHeight = 20 # the x/y header height
    footerHeight = 30 # the message at the bottom height
    markWidth = 26 # row-number/exclusion column width
    deleteWidth = 20 # delete column width
    padding = 8 # empty space between the panel border and table

    def __init__(self, panel):
        self.panel = panel 
        # which cell is being typed into. None means nothing is being edited.
        self.editRow, self.editCol = None, None
        self.currNum = ''
        self.errorMessage = ''
        # the blank row at the bottom. Its two cells are plain strings until
        # both parse, at which point the row becomes a real DataPoint.
        self.draftX, self.draftY = '', ''
        self.scrollTop = 0

        left = panel.left + DataTable.padding
        usableWidth = panel.width - 2 * DataTable.padding
        valueWidth = (usableWidth - DataTable.markWidth - DataTable.deleteWidth) / 2
        self.markLeft = left
        self.xLeft = left + DataTable.markWidth
        self.yLeft = self.xLeft + valueWidth
        self.deleteLeft = self.yLeft + valueWidth
        self.valueWidth = valueWidth
        self.rowsTop = panel.contentTop() + DataTable.headerHeight


    # count how many rows can fit between the header and footer
    def visibleRowCount(self):
        space = self.panel.bottom - self.rowsTop - DataTable.footerHeight
        return max(1, int(space // DataTable.rowHeight))

    # the draft row sits one past the last real point
    def totalRowCount(self, data):
        return len(data.points) + 1

    # calculate height of row that should be visible on the top, not necessairly first data
    def rowTop(self, screenIndex):
        return self.rowsTop + screenIndex * DataTable.rowHeight

    # which (row, column) a click landed on, or None.
    # column 0 is x, column 1 is y, 'mark' toggles exclusion, 'delete' removes.
    def cellAt(self, mouseX, mouseY, data):
        if not (self.rowsTop <= mouseY < self.rowsTop +
                self.visibleRowCount() * DataTable.rowHeight):
            return None
        screenIndex = int((mouseY - self.rowsTop) // DataTable.rowHeight)
        row = self.scrollTop + screenIndex
        if row >= self.totalRowCount(data):
            return None
        if self.markLeft <= mouseX < self.xLeft:
            return (row, 'mark')
        if self.xLeft <= mouseX < self.yLeft:
            return (row, 0)
        if self.yLeft <= mouseX < self.deleteLeft:
            return (row, 1)
        if self.deleteLeft <= mouseX < self.deleteLeft + DataTable.deleteWidth:
            return (row, 'delete')
        return None

    # when editing, self.editRow will have a row of a cell being edited
    def isEditing(self):
        return self.editRow is not None

    # real points will take row from 0 to len(data.points)-1
    def isDraftRow(self, row, data):
        return row == len(data.points)

    # text that should appear in a cell
    def currentText(self, row, col, data):
        if self.isDraftRow(row, data):
            return self.draftX if col == 0 else self.draftY
        point = data.points[row]
        return formatCell(point.x if col == 0 else point.y)

    # make sure the row is legal then edit
    def startEdit(self, row, col, data):
        if row < 0 or row >= self.totalRowCount(data):
            self.cancelEdit()
            return
        self.editRow, self.editCol = row, col
        self.currNum = self.currentText(row, col, data)
        self.errorMessage = ''
        self.scrollToRow(row)

    def cancelEdit(self):
        self.editRow, self.editCol = None, None
        self.currNum = ''
        self.errorMessage = ''

    # make sure the target row is visible in the table
    def scrollToRow(self, targetRow):
        # if the target row is less than the top, simply make the top the target row
        if targetRow < self.scrollTop:
            self.scrollTop = targetRow

        # if the target row is larger than the last visible row of the table,
        # make the target row be the last row in the table
        lastVisible = self.scrollTop + self.visibleRowCount() - 1
        if targetRow > lastVisible:
            self.scrollTop = targetRow - self.visibleRowCount() + 1
        if self.scrollTop < 0:
            self.scrollTop = 0

    def scrollBy(self, rows, data):
        highest = max(0, self.totalRowCount(data) - self.visibleRowCount())
        self.scrollTop = min(highest, max(0, self.scrollTop + rows))


    # adds self.currNum into the Dataset. Returns True when the value was
    # in case it's illegal, the currNum is kept so the user can correct it.
    def commitCell(self, data):
        if not self.isEditing():
            return True
        works, message = dataset.parseNumber(self.currNum)
        if not works:
            self.errorMessage = message
            return False
        self.errorMessage = ''
        value = message

        # in case the selected cell is no the draft cell
        if not self.isDraftRow(self.editRow, data):
            point = data.points[self.editRow]
            if self.editCol == 0:
                data.editPoint(self.editRow, value, point.y)
            else:
                data.editPoint(self.editRow, point.x, value)
            return True

        # the draft row
        # it will hold the value until the row is fully edited
        # holds value only if the value is valid
        if self.editCol == 0:
            self.draftX = self.currNum
        else:
            self.draftY = self.currNum
        if self.draftX != '' and self.draftY != '':
            okX, xValue = dataset.parseNumber(self.draftX)
            okY, yValue = dataset.parseNumber(self.draftY)
            if okX and okY:
                data.addPoint(xValue, yValue)
                self.draftX, self.draftY = '', ''
        return True

    # x -> y -> next row's x
    def advance(self, data):
        row, col = self.editRow, self.editCol
        if col == 0:
            self.startEdit(row, 1, data)
        else:
            self.startEdit(min(row + 1, len(data.points)), 0, data)


    # Returns True when the table used the key, so main.py knows not to treat
    # it as a global shortcut.
    def handleKey(self, key, data):
        if not self.isEditing():
            return False
        if key == 'escape':
            self.cancelEdit()
        elif key == 'backspace':
            self.currNum = self.currNum[:-1]
            self.errorMessage = ''
        elif key in ('enter', 'return', ','):
            if self.commitCell(data):
                self.advance(data)
        elif key == 'tab':
            if self.commitCell(data):
                self.advance(data)
        elif key == 'space':
            pass
        elif len(key) == 1:
            # anything printable is accepted so that parseNumber can give a
            # real message about it rather than the key silently doing nothing
            self.currNum += key
            self.errorMessage = ''
        else:
            return False
        return True

    # Returns an action string for main.py, or None. The table performs its
    # own edits but never deletes or excludes on its own.
    def handleClick(self, mouseX, mouseY, data):
        hit = self.cellAt(mouseX, mouseY, data)
        if hit is None:
            if self.isEditing():
                self.commitCell(data)
                self.cancelEdit()
            return None
        row, col = hit
        if col in (0, 1):
            if self.isEditing():
                self.commitCell(data)
            self.startEdit(row, col, data)
            return None
        if self.isDraftRow(row, data):
            return None
        if self.isEditing():
            self.commitCell(data)
            self.cancelEdit()
        return (col, row)


    def draw(self, data):
        self.drawHeader()
        firstRow = self.scrollTop
        for screenIndex in range(self.visibleRowCount()):
            row = firstRow + screenIndex
            if row >= self.totalRowCount(data):
                break
            self.drawRow(row, screenIndex, data)
        self.drawFooter(data)

    def drawHeader(self):
        top = self.panel.contentTop()
        drawLabel('#', self.markLeft + DataTable.markWidth / 2,
                  top + DataTable.headerHeight / 2, size=10, fill=mutedColor)
        drawLabel('x', self.xLeft + self.valueWidth / 2,
                  top + DataTable.headerHeight / 2, size=10, bold=True)
        drawLabel('y', self.yLeft + self.valueWidth / 2,
                  top + DataTable.headerHeight / 2, size=10, bold=True)
        drawLine(self.markLeft, self.rowsTop,
                 self.deleteLeft + DataTable.deleteWidth, self.rowsTop,
                 fill=panelBorder)

    def drawRow(self, row, screenIndex, data):
        top = self.rowTop(screenIndex)
        isDraft = self.isDraftRow(row, data)
        excluded = (not isDraft) and data.points[row].isExcluded

        if self.isEditing() and self.editRow == row:
            drawRect(self.markLeft, top,
                     self.deleteLeft + DataTable.deleteWidth - self.markLeft,
                     DataTable.rowHeight, fill=selectFill)

        # the row number doubles as the exclude toggle
        if isDraft:
            drawLabel('+', self.markLeft + DataTable.markWidth / 2,
                      top + DataTable.rowHeight / 2, size=11, fill=mutedColor)
        else:
            drawLabel(str(row + 1), self.markLeft + DataTable.markWidth / 2,
                      top + DataTable.rowHeight / 2, size=10,
                      fill=mutedColor if not excluded else errorColor)

        self.drawCell(row, 0, self.xLeft, top, data, isDraft, excluded)
        self.drawCell(row, 1, self.yLeft, top, data, isDraft, excluded)

        if not isDraft:
            drawLabel('x', self.deleteLeft + DataTable.deleteWidth / 2,
                      top + DataTable.rowHeight / 2, size=10, fill=mutedColor)

    def drawCell(self, row, col, left, top, data, isDraft, excluded):
        editing = self.isEditing() and self.editRow == row and self.editCol == col
        if editing:
            drawRect(left, top, self.valueWidth, DataTable.rowHeight,
                     fill=editFill, border=panelBorder)
            text = self.currNum + '|'
            fill = textColor
        else:
            text = self.currentText(row, col, data)
            if text == '':
                text = '-' if isDraft else ''
            fill = mutedColor if (isDraft or excluded) else textColor
        drawLabel(text, left + 5, top + DataTable.rowHeight / 2,
                  size=11, align='left', fill=fill)

    def drawFooter(self, data):
        top = self.panel.bottom - DataTable.footerHeight
        drawLine(self.markLeft, top, self.deleteLeft + DataTable.deleteWidth,
                 top, fill=panelBorder)
        if self.errorMessage != '':
            drawLabel(self.errorMessage, self.markLeft, top + 11,
                      size=10, align='left', fill=errorColor)
            drawLabel('Esc cancels', self.markLeft, top + 23,
                      size=9, align='left', fill=mutedColor)
        elif self.isEditing():
            drawLabel('comma or enter = next cell', self.markLeft, top + 11,
                      size=9, align='left', fill=mutedColor)
            drawLabel('esc cancels, click x deletes', self.markLeft, top + 23,
                      size=9, align='left', fill=mutedColor)
        else:
            active = data.getActiveCount()
            drawLabel(f'{len(data.points)} rows, {active} active',
                      self.markLeft, top + 11, size=10, align='left',
                      fill=mutedColor)
            drawLabel('click a cell to edit, # to exclude', self.markLeft,
                      top + 23, size=9, align='left', fill=mutedColor)

def wrapText(text, maxChars):
    words = text.split(' ')
    lines, current = [], ''
    for word in words:
        candidate = word if current == '' else current + ' ' + word
        if len(candidate) <= maxChars:
            current = candidate
        else:
            if current != '':
                lines.append(current)
            current = word
    if current != '':
        lines.append(current)
    return lines

def formatScore(value, decimals = 4):
    if value is None:
        return 'n/a'
    # a tiny score is still worth telling apart from a true zero
    if value != 0 and abs(value) < 0.001:
        return f'{value:.4g}'
    return f'{value:.{decimals}f}'

class ModelCards:
    rowHeight = 25
    swatchSize = 9
    lineHeight = 12
    wrapWidth = 44

    def __init__(self, panel):
        self.panel = panel
        # which row is open. It doubles as the selection for the residual plot.
        self.expandedIndex = 0
        self.left = panel.left + 10
        self.width = panel.width - 20
        # the verdict hides behind a button in the panel's title bar,
        # like the graph window's own Window button
        self.showVerdict = False
        self.verdictButton = Button(panel.right - 74, panel.top + 3, 64, 20,
                                    'Verdict', 'toggleVerdict')

    def expandedHeight(self, result):
        height = 6
        height += ModelCards.lineHeight * len(
            wrapText(result.getEquation(), ModelCards.wrapWidth))
        height += ModelCards.lineHeight * 2 + 2
        if result.isAdjusted():
            height += ModelCards.lineHeight
        for warning in result.interpretations:
            height += 10 * len(wrapText(warning, ModelCards.wrapWidth)) + 4
        return height + 6

    # the engine's one-sentence conclusion sits at the very top, in its
    # own box so it reads before any of the numbers
    def verdictLines(self, analysisEngine):
        if not self.showVerdict:
            return []
        return wrapText(analysisEngine.verdict(), ModelCards.wrapWidth)

    def verdictHeight(self, analysisEngine):
        lines = self.verdictLines(analysisEngine)
        if len(lines) == 0:
            return 0
        return 10 * len(lines) + 26

    def drawVerdict(self, analysisEngine):
        lines = self.verdictLines(analysisEngine)
        if len(lines) == 0:
            return
        top = self.panel.contentTop() + 6
        drawRect(self.left - 4, top, self.width + 8, 10 * len(lines) + 20,
                 fill=selectFill, border=accentColor)
        drawLabel('verdict', self.left + 4, top + 8, size=9, align='left',
                  bold=True, fill=accentColor)
        y = top + 18
        for line in lines:
            drawLabel(line, self.left + 4, y, size=9, align='left')
            y += 10

    # the dataset's own cautions (too few points, repeated x-values) sit
    # above the cards, because they qualify the whole ranking at once
    def warningLines(self, analysisEngine):
        if len(analysisEngine.results) == 0:
            return []
        lines = []
        for warning in analysisEngine.dataset.getWarnings():
            lines.extend(wrapText(warning, ModelCards.wrapWidth))
        return lines

    # how far the warning box pushes the cards down
    def warningsHeight(self, analysisEngine):
        lines = self.warningLines(analysisEngine)
        if len(lines) == 0:
            return 0
        return 10 * len(lines) + 16

    def drawWarnings(self, analysisEngine):
        lines = self.warningLines(analysisEngine)
        if len(lines) == 0:
            return
        top = self.panel.contentTop() + 6 + self.verdictHeight(analysisEngine)
        drawRect(self.left - 4, top, self.width + 8, 10 * len(lines) + 10,
                 fill=warningFill, border=panelBorder)
        y = top + 8
        for line in lines:
            drawLabel(line, self.left + 4, y, size=9, align='left')
            y += 10

    # (index, top, totalHeight) for every result
    def rowLayout(self, analysisEngine):
        layout = []
        top = self.panel.contentTop() + 6 + self.verdictHeight(analysisEngine) \
              + self.warningsHeight(analysisEngine)
        for i in range(len(analysisEngine.results)):
            height = ModelCards.rowHeight
            if i == self.expandedIndex:
                height += self.expandedHeight(analysisEngine.results[i])
            layout.append((i, top, height))
            top += height
        return layout

    def selectedResult(self, analysisEngine):
        if self.expandedIndex is None:
            return None
        if 0 <= self.expandedIndex < len(analysisEngine.results):
            return analysisEngine.results[self.expandedIndex]
        return None

    def selectedName(self, analysisEngine):
        result = self.selectedResult(analysisEngine)
        if result is None:
            return None
        return result.model.name

    # points expandedIndex back at the model that was open before a refit,
    # since the same model may now sit at a different rank
    def reselect(self, analysisEngine, name):
        if name is None:
            return
        for i in range(len(analysisEngine.results)):
            if analysisEngine.results[i].model.name == name:
                self.expandedIndex = i
                return
        # that model could not be fitted anymore, so fall back to the winner
        self.expandedIndex = 0

    # return ('toggle', index) when the swatch was hit, ('select', index) for the
    # row itself, or None
    def handleClick(self, mouseX, mouseY, analysisEngine):
        if not (self.left - 4 <= mouseX <= self.left + self.width + 4):
            return None
        for index, top, height in self.rowLayout(analysisEngine):
            if top <= mouseY < top + ModelCards.rowHeight:
                if mouseX < self.left + 14:
                    return ('toggle', index)
                return ('select', index)
        return None

    ########################################################################
    # written by Claude Opus 5 / Jul 30, 2026
    ########################################################################

    def draw(self, analysisEngine, colorForResult):
        self.verdictButton.draw(pressed=self.showVerdict)
        if len(analysisEngine.results) == 0:
            drawLabel('No model fitted yet.', self.left,
                      self.panel.contentTop() + 16, size=11, align='left',
                      fill=mutedColor)
            drawLabel('Add points, or try a sample above.', self.left,
                      self.panel.contentTop() + 32, size=11, align='left',
                      fill=mutedColor)
            return

        self.drawVerdict(analysisEngine)
        self.drawWarnings(analysisEngine)
        bottom = self.panel.bottom - 8
        for index, top, height in self.rowLayout(analysisEngine):
            if top > bottom:
                break
            result = analysisEngine.results[index]
            self.drawRow(result, index, top, colorForResult(result))
            if index == self.expandedIndex:
                self.drawDetail(result, top + ModelCards.rowHeight)

        self.drawFooter(analysisEngine)

    def drawRow(self, result, index, top, color):
        middle = top + ModelCards.rowHeight / 2
        if index == self.expandedIndex:
            drawRect(self.left - 4, top, self.width + 8,
                     ModelCards.rowHeight, fill=selectFill)
            drawRect(self.left - 4, top, 3, ModelCards.rowHeight,
                     fill=accentColor)

        # a filled swatch means the curve is on the graph, hollow means off
        size = ModelCards.swatchSize
        if result.isVisible:
            drawRect(self.left, middle - size / 2, size, size, fill=color)
        else:
            drawRect(self.left, middle - size / 2, size, size,
                     fill=None, border=mutedColor)

        drawLabel(f'{index + 1}. {result.model.name}', self.left + 16, middle,
                  size=11, align='left', bold=(index == self.expandedIndex))
        drawLabel(formatScore(result.cvRmse), self.left + self.width, middle,
                  size=11, align='right', fill=mutedColor)

    def drawDetail(self, result, top):
        y = top + 8
        for line in wrapText(result.getEquation(), ModelCards.wrapWidth):
            drawLabel(line, self.left + 16, y, size=10, align='left')
            y += ModelCards.lineHeight

        drawLabel(f'training RMSE {formatScore(result.trainRmse)}     '
                  f'R2 {formatScore(result.r2)}',
                  self.left + 16, y, size=9, align='left', fill=mutedColor)
        y += ModelCards.lineHeight

        # an akaike weight is a share of support, so a bar reads faster
        # than the number on its own
        if result.akaikeWeight is None:
            drawLabel('AICc n/a: too few points for this many parameters',
                      self.left + 16, y, size=9, align='left', fill=mutedColor)
        else:
            barWidth = 84
            drawRect(self.left + 16, y - 4, barWidth, 8, fill=titleFill)
            filledWidth = barWidth * result.akaikeWeight
            if filledWidth < 1:
                filledWidth = 1
            drawRect(self.left + 16, y - 4, filledWidth, 8,
                     fill=mutedColor)
            drawLabel(f'{result.akaikeWeight * 100:.0f}% of AICc support',
                      self.left + 16 + barWidth + 8, y, size=9, align='left',
                      fill=mutedColor)
        y += ModelCards.lineHeight + 2

        if result.isAdjusted():
            drawLabel('adjusted by hand: CV and AICc no longer apply',
                      self.left + 16, y, size=9, align='left', fill=errorColor)
            y += ModelCards.lineHeight

        for warning in result.interpretations:
            for line in wrapText(warning, ModelCards.wrapWidth):
                drawLabel(line, self.left + 16, y, size=9, align='left',
                          fill=errorColor)
                y += 10
            y += 4

    def drawFooter(self, analysisEngine):
        # ties are covered by the verdict box now, so the footer only
        # lists the models that could not be fitted
        y = self.panel.bottom - 12
        for name, reason in analysisEngine.unavailable:
            drawLabel(f'{name}: {reason}'[:48], self.left, y, size=9,
                      align='left', fill=mutedColor)
            y -= 11
        if len(analysisEngine.unavailable) > 0:
            drawLabel('not fitted', self.left, y, size=9, align='left',
                      bold=True, fill=mutedColor)
    ########################################################################

# the Sample button in the header. Clicking it drops down one button per
# sample dataset, and the one currently loaded stays highlighted.
class SampleMenu:
    rowHeight = 24
    width = 150

    def __init__(self, left, top):
        self.isOpen = False
        self.button = Button(left, top, 64, 24, 'Sample', 'toggleSamples')
        menuLeft = left + 64 - SampleMenu.width
        menuTop = top + 24 + 4
        self.rows = []
        for i in range(len(dataset.samples)):
            self.rows.append(Button(menuLeft,
                                    menuTop + i * SampleMenu.rowHeight,
                                    SampleMenu.width, SampleMenu.rowHeight,
                                    dataset.samples[i][0], f'sample{i}'))

    # returns an action string for main.py, or None when the click was
    # not ours. Opening, choosing, and closing all happen here.
    def handleClick(self, mouseX, mouseY):
        if self.button.contains(mouseX, mouseY):
            self.isOpen = not self.isOpen
            return 'toggled'
        if not self.isOpen:
            return None
        for row in self.rows:
            if row.contains(mouseX, mouseY):
                self.isOpen = False
                return row.action
        # a click anywhere else closes the menu and is swallowed, so
        # dismissing it never also drops a point onto the graph
        self.isOpen = False
        return 'closed'

    def drawButton(self, isPressed = False):
        self.button.draw(pressed=(self.isOpen or isPressed), primary=True)

    # drawn late in redrawAll so the open menu sits above the panels
    def drawMenu(self, activeIndex):
        if not self.isOpen:
            return
        for i in range(len(self.rows)):
            self.rows[i].draw(pressed=(i == activeIndex))


class HelpOverlay:
    cardWidth = 560
    cardHeight = 400

    about = [
        'Models are ranked by how well they predict points they were',
        'not fitted on (cross-validated RMSE), not by how closely they',
        'hug the points they already saw. That is why a high R2 can',
        'still lose: a flexible model can memorize noise instead of',
        'finding the pattern. The Verdict button, the warnings, and',
        'the Influence tab all show how far the winner can be trusted.',
    ]

    shortcuts = [
        ('s', 'load the next sample dataset'),
        ('u', 'undo the last data change'),
        ('f', 'reframe the graph around the data'),
        ('arrows', 'pan the graph window'),
        ('+ / -', 'zoom the graph in and out'),
        ('r p v i q', 'pick the tab under the graph'),
        ('1 - 7', 'expand the model card at that rank'),
        ('up / down', 'scroll the table while editing'),
        ('h', 'open and close this help'),
    ]

    def __init__(self, windowWidth, windowHeight):
        self.isOpen = False
        self.windowWidth, self.windowHeight = windowWidth, windowHeight
        self.left = (windowWidth - HelpOverlay.cardWidth) / 2
        self.top = (windowHeight - HelpOverlay.cardHeight) / 2

    def draw(self):
        if not self.isOpen:
            return
        drawRect(0, 0, self.windowWidth, self.windowHeight, fill='black',
                 opacity=40)
        drawRect(self.left, self.top, HelpOverlay.cardWidth,
                 HelpOverlay.cardHeight, fill='white', border=panelBorder)
        x = self.left + 24
        y = self.top + 28
        drawLabel('How VeriFit decides', x, y, size=14, bold=True,
                  align='left')
        y += 22
        for line in HelpOverlay.about:
            drawLabel(line, x, y, size=11, align='left')
            y += 16
        y += 14
        drawLabel('Shortcuts', x, y, size=14, bold=True, align='left')
        y += 22
        for keys, what in HelpOverlay.shortcuts:
            drawLabel(keys, x, y, size=11, bold=True, align='left')
            drawLabel(what, x + 100, y, size=11, align='left')
            y += 17
        drawLabel('press any key or click anywhere to close', x,
                  self.top + HelpOverlay.cardHeight - 16, size=10,
                  align='left', fill=mutedColor)


class PredictPanel:
    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.buffer = ''
        self.value = None
        self.isEditing = False
        self.boxLeft = left + 26
        self.boxTop = top + 6
        self.boxWidth, self.boxHeight = 110, 20

    def boxContains(self, mouseX, mouseY):
        return (self.boxLeft <= mouseX <= self.boxLeft + self.boxWidth and
                self.boxTop <= mouseY <= self.boxTop + self.boxHeight)

    # called when the user drags the marker on the graph instead of typing
    def setValue(self, x):
        self.value = x
        self.buffer = formatCell(x)
        self.isEditing = False

    def handleClick(self, mouseX, mouseY):
        self.isEditing = self.boxContains(mouseX, mouseY)
        return self.isEditing

    def handleKey(self, key):
        if not self.isEditing:
            return False
        if key == 'escape':
            self.isEditing = False
        elif key == 'backspace':
            self.buffer = self.buffer[:-1]
            self.commit()
        elif key in ('enter', 'return'):
            self.commit()
            self.isEditing = False
        elif len(key) == 1:
            self.buffer += key
            self.commit()
        else:
            return False
        return True

    def commit(self):
        works, result = dataset.parseNumber(self.buffer)
        self.value = result if works else None

    def draw(self, data, analysisEngine, result, colorForResult):
        drawLabel('x =', self.left, self.boxTop + self.boxHeight / 2, size=11,
                  align='left')
        drawRect(self.boxLeft, self.boxTop, self.boxWidth, self.boxHeight,
                 fill=editFill if self.isEditing else 'white',
                 border=panelBorder)
        shown = self.buffer + ('|' if self.isEditing else '')
        drawLabel(shown, self.boxLeft + 5, self.boxTop + self.boxHeight / 2,
                  size=11, align='left')
        drawLabel('or drag on the graph',
                  self.boxLeft + self.boxWidth + 10,
                  self.boxTop + self.boxHeight / 2, size=9, align='left',
                  fill=mutedColor)

        if self.value is None:
            drawLabel('Type an x value to predict at.', self.left,
                      self.top + 44, size=10, align='left', fill=mutedColor)
            return

        # one line per visible model, so competing predictions can be
        # compared, each with the range a new point would likely land in
        y = self.top + 42
        shownAny = False
        for candidate in analysisEngine.results:
            if not candidate.isVisible:
                continue
            guess = analysisEngine.predictAt(candidate, self.value)
            text = 'cannot predict here' if guess is None else formatScore(guess, 3)
            drawLabel(f'{candidate.model.name}', self.left, y, size=10,
                      align='left', fill=colorForResult(candidate))
            drawLabel(f'y = {text}', self.left + 96, y, size=10, align='left')
            band = analysisEngine.bandAt(candidate, self.value)
            if band is not None:
                drawLabel(f'likely {formatScore(band[0], 3)} '
                          f'to {formatScore(band[1], 3)}',
                          self.left + 210, y, size=10, align='left',
                          fill=mutedColor)
            y += 14
            shownAny = True
        if not shownAny:
            drawLabel('No curve is switched on.', self.left, y, size=10,
                      align='left', fill=mutedColor)

        if data.isExtrapolation(self.value):
            boxLeft = self.left + self.width - 210
            drawRect(boxLeft, self.top + 2, 204, 32,
                     fill=warningFill, border=errorColor)
            drawLabel('outside the data range', boxLeft + 8,
                      self.top + 12, size=10, align='left', fill=errorColor)
            drawLabel('watch the bands widen out here', boxLeft + 8,
                      self.top + 26, size=9, align='left', fill=mutedColor)

class SensitivityPanel:
    rowGap = 22

    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.sliders = []
        for i in range(4):
            self.sliders.append(Slider(left, top + 24 + i * SensitivityPanel.rowGap,
                                       width - 90))
        self.draggingIndex = None
        self.resetButton = Button(left + width - 74, top + 6, 70, 20,
                                  'Reset', 'resetParams')

    def parameterName(self, result, index):
        model = result.model
        if hasattr(model, 'powers'):
            power = model.powers[index]
            if power == 0:
                return 'constant'
            if power == 1:
                return 'x coefficient'
            return f'x^{power} coefficient'
        if model.name == 'Flatline':
            return 'c'
        return 'a' if index == 0 else 'b'

    def usableCount(self, result):
        if result is None or result.parameterBounds is None:
            return 0
        return min(len(result.parameterBounds), len(self.sliders))

    # which slider a press landed on, or None
    def sliderAt(self, mouseX, mouseY, result):
        for i in range(self.usableCount(result)):
            if self.sliders[i].contains(mouseX, mouseY):
                return i
        return None

    # returns a new parameter list for the model, or None if nothing moved
    def valueFromDrag(self, mouseX, result):
        if self.draggingIndex is None or result is None:
            return None
        i = self.draggingIndex
        if i >= self.usableCount(result):
            return None
        low, high = result.parameterBounds[i]
        params = list(result.model.params)
        params[i] = self.sliders[i].valueAt(mouseX, low, high)
        return params

    def draw(self, result):
        if result is None:
            drawLabel('Select a model first.', self.left, self.top + 14,
                      size=10, align='left', fill=mutedColor)
            return
        if result.parameterBounds is None:
            drawLabel('No standard errors for this model.', self.left,
                      self.top + 14, size=10, align='left', fill=mutedColor)
            drawLabel('It needs more points than it has parameters.',
                      self.left, self.top + 28, size=9, align='left',
                      fill=mutedColor)
            return

        drawLabel(f'{result.model.name}: drag within plus or minus 2 standard errors',
                  self.left, self.top+6, size=9, align='left', fill=mutedColor)
        for i in range(self.usableCount(result)):
            low, high = result.parameterBounds[i]
            self.sliders[i].draw(self.parameterName(result, i),
                                 result.model.params[i], low, high,
                                 result.isAdjusted())
        self.resetButton.draw()
        if result.isAdjusted():
            drawLabel('dashed line is the original fit', self.left,
                      self.top + 14 + self.usableCount(result) * SensitivityPanel.rowGap,
                      size=9, align='left', fill=errorColor)

# Outlier influence. One bar per point, on the same x axis as the graph
# above, so a tall bar sits directly under the point that caused it.
class InfluencePanel:
    barWidth = 7

    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.barsTop = top + 34
        self.barsBottom = top + height - 12

    def toScreenX(self, x, xMin, xMax):
        if xMax <= xMin:
            return self.left
        return self.left + (x - xMin) / (xMax - xMin) * self.width

    # the tallest shift sets the scale, so the bars are always readable
    def biggestShift(self, report):
        biggest = 0
        for entry in report:
            if entry.cvShift is not None and abs(entry.cvShift) > biggest:
                biggest = abs(entry.cvShift)
        return biggest

    def drawVerdict(self, winner, report):
        changers = []
        for entry in report:
            if entry.changesWinner:
                changers.append(entry)
        if len(changers) == 0:
            drawLabel(f'{winner} stays the best model no matter which single '
                      f'point is removed.', self.left, self.top + 8, size=10,
                      align='left')
            drawLabel('The ranking does not depend on any one point.',
                      self.left, self.top + 22, size=9, align='left',
                      fill=mutedColor)
            return
        first = changers[0]
        drawLabel(f'Removing row {first.row + 1} changes the best model from '
                  f'{winner} to {first.winner}.', self.left, self.top + 8,
                  size=10, align='left', fill=influenceAlertColor)
        if len(changers) == 1:
            drawLabel('The conclusion rests on that one point. Try excluding it.',
                      self.left, self.top + 22, size=9, align='left',
                      fill=mutedColor)
        else:
            rows = []
            for entry in changers:
                rows.append(str(entry.row + 1))
            drawLabel(f'{len(changers)} points change the answer on their own: '
                      f'rows {", ".join(rows)}.', self.left, self.top + 22,
                      size=9, align='left', fill=mutedColor)

    def draw(self, sweep, data, xMin, xMax):
        if sweep is None:
            drawLabel('Not enough points yet - the sweep needs at least four.',
                      self.left, self.top + 20, size=10, align='left',
                      fill=mutedColor)
            return
        winner, report = sweep
        self.drawVerdict(winner, report)

        drawLine(self.left, self.barsBottom, self.left + self.width,
                 self.barsBottom, fill=panelBorder)
        biggest = self.biggestShift(report)
        if biggest <= 0:
            return
        usableHeight = self.barsBottom - self.barsTop
        xs = data.getRawXs()
        for entry in report:
            if entry.activeIndex >= len(xs) or entry.cvShift is None:
                continue
            pixelX = self.toScreenX(xs[entry.activeIndex], xMin, xMax)
            if not (self.left <= pixelX <= self.left + self.width):
                continue
            barHeight = abs(entry.cvShift) / biggest * usableHeight
            if barHeight < 1:
                barHeight = 1
            color = influenceAlertColor if entry.changesWinner else influenceBarColor
            drawRect(pixelX - InfluencePanel.barWidth / 2,
                     self.barsBottom - barHeight,
                     InfluencePanel.barWidth, barHeight, fill=color)
            if entry.changesWinner:
                drawLabel(str(entry.row + 1), pixelX,
                          self.barsBottom - barHeight - 7, size=9,
                          fill=influenceAlertColor)
        drawLabel('how much the winner\'s error moves when each point is dropped',
                  self.left, self.barsBottom + 7, size=9, align='left',
                  fill=mutedColor)


########################################################################
# written by Claude Opus 5 / Jul 31, 2026
########################################################################
class RSquaredPanel:
    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.leftColumn = left + 74
        self.rightColumn = left + width - 74
        self.rowsTop = top + 26

    # models sorted best-first by whichever statistic, ignoring the ones
    # that have no value for it
    def rankedBy(self, results, useRSquared):
        usable = []
        for result in results:
            value = result.r2 if useRSquared else result.cvRmse
            if value is not None:
                usable.append((value, result))
        # a high R-squared is good, a low CV RMSE is good
        usable.sort(key=lambda pair: -pair[0] if useRSquared else pair[0])
        ordered = []
        for value, result in usable:
            ordered.append(result)
        return ordered

    def rowY(self, index, total):
        if total <= 1:
            return self.rowsTop + 10
        space = self.height - 38
        return self.rowsTop + index * (space / max(1, total - 1))

    def draw(self, analysisEngine, colorForResult):
        byR2 = self.rankedBy(analysisEngine.results, True)
        byCv = self.rankedBy(analysisEngine.results, False)
        if len(byR2) == 0 or len(byCv) == 0:
            drawLabel('No scores to compare yet.', self.left, self.top + 20,
                      size=10, align='left', fill=mutedColor)
            return

        drawLabel('ranked by R2', self.leftColumn, self.top + 10, size=9,
                  align='right', fill=mutedColor)
        drawLabel('ranked by CV RMSE', self.rightColumn + 6, self.top + 10,
                  size=9, align='left', fill=mutedColor)

        # join each model to itself; a crossing line is a disagreement
        for leftIndex in range(len(byR2)):
            result = byR2[leftIndex]
            if result not in byCv:
                continue
            rightIndex = byCv.index(result)
            y1 = self.rowY(leftIndex, len(byR2))
            y2 = self.rowY(rightIndex, len(byCv))
            crossed = (leftIndex != rightIndex)
            drawLine(self.leftColumn + 4, y1, self.rightColumn - 4, y2,
                     fill=colorForResult(result) if crossed else slopeLineColor,
                     lineWidth=2 if crossed else 1)

        for index in range(len(byR2)):
            result = byR2[index]
            drawLabel(f'{result.model.name} {formatScore(result.r2, 3)}',
                      self.leftColumn, self.rowY(index, len(byR2)), size=9,
                      align='right', fill=colorForResult(result))
        for index in range(len(byCv)):
            result = byCv[index]
            drawLabel(f'{result.model.name} {formatScore(result.cvRmse, 3)}',
                      self.rightColumn + 6, self.rowY(index, len(byCv)),
                      size=9, align='left', fill=colorForResult(result))

        if len(byR2) > 0 and len(byCv) > 0 and byR2[0] is not byCv[0]:
            drawLabel(f'R2 prefers {byR2[0].model.name}, cross-validation '
                      f'prefers {byCv[0].model.name}.',
                      self.left, self.top + self.height, size=9,
                      align='left', fill=errorColor)
        else:
            drawLabel('Both statistics agree on the winner here.', self.left,
                      self.top + self.height - 6, size=9, align='left',
                      fill=mutedColor)
            

# ======================================================================
# The graph window settings.
#
# A small button in the Graph panel's title bar opens a popover with the
# window written the way it reads out loud:
#
#       ____ < x < ____
#       ____ < y < ____
#
# The fields hold no values of their own. When idle each reads straight
# from the GraphView, so the numbers can never drift out of step with what
# is on screen, and they double as a readout after Reframe moves the view.
# ======================================================================

class WindowControls:
    boxWidth = 78
    boxHeight = 22
    rowGap = 30
    padding = 12
    signWidth = 44

    def __init__(self, panel):
        self.panel = panel
        self.isOpen = False
        # which box is being typed into. None means none.
        self.editIndex = None
        self.buffer = ''
        self.errorMessage = ''

        self.width = 2 * WindowControls.padding + 2 * WindowControls.boxWidth \
                     + WindowControls.signWidth
        self.height = 2 * WindowControls.padding + WindowControls.boxHeight \
                      + WindowControls.rowGap
        self.left = panel.right - self.width - 12
        self.top = panel.contentTop() + 6

        # the opener sits in the panel's own title bar
        self.toggleButton = Button(panel.right - 78, panel.top + 3, 68, 20,
                                   'Window', 'toggleWindow')

    # ---------- geometry ----------

    # index 0 and 1 are the x row, 2 and 3 are the y row
    def boxLeft(self, index):
        if index % 2 == 0:
            return self.left + WindowControls.padding
        return (self.left + WindowControls.padding + WindowControls.boxWidth
                + WindowControls.signWidth)

    def boxTop(self, index):
        row = index // 2
        return self.top + WindowControls.padding + row * WindowControls.rowGap

    def boxAt(self, mouseX, mouseY):
        for index in range(4):
            left, top = self.boxLeft(index), self.boxTop(index)
            if (left <= mouseX <= left + WindowControls.boxWidth and
                    top <= mouseY <= top + WindowControls.boxHeight):
                return index
        return None

    def contains(self, mouseX, mouseY):
        return (self.left <= mouseX <= self.left + self.width and
                self.top <= mouseY <= self.top + self.height)

    # ---------- values ----------

    # the four bounds in the order the boxes appear
    def boundsOf(self, graph):
        return [graph.xMin, graph.xMax, graph.yMin, graph.yMax]

    def currentText(self, graph, index):
        return formatCell(self.boundsOf(graph)[index])

    def startEdit(self, graph, index):
        self.editIndex = index
        self.buffer = self.currentText(graph, index)
        self.errorMessage = ''

    def cancelEdit(self):
        self.editIndex = None
        self.buffer = ''
        self.errorMessage = ''

    def close(self, graph):
        self.commit(graph)
        self.cancelEdit()
        self.isOpen = False

    # Applies the typed value, keeping the other three as they are. Returns
    # True when it was accepted; on failure the text is kept so the user can
    # correct it rather than losing what they typed.
    def commit(self, graph):
        if self.editIndex is None:
            return True
        works, result = dataset.parseNumber(self.buffer)
        if not works:
            self.errorMessage = result
            return False
        bounds = self.boundsOf(graph)
        bounds[self.editIndex] = result
        # setWindow would quietly widen a backwards window, which would put
        # the user somewhere they did not ask for. Refuse and say why.
        if bounds[1] <= bounds[0]:
            self.errorMessage = 'x min must be below x max'
            return False
        if bounds[3] <= bounds[2]:
            self.errorMessage = 'y min must be below y max'
            return False
        self.errorMessage = ''
        graph.setWindow(bounds[0], bounds[1], bounds[2], bounds[3])
        return True

    # ---------- input ----------

    # returns True when the click belonged to these controls
    def handleClick(self, mouseX, mouseY, graph):
        if self.toggleButton.contains(mouseX, mouseY):
            if self.isOpen:
                self.close(graph)
            else:
                self.isOpen = True
            return True
        if not self.isOpen:
            return False

        index = self.boxAt(mouseX, mouseY)
        if index is not None:
            if self.editIndex is not None and self.editIndex != index:
                self.commit(graph)
            self.startEdit(graph, index)
            return True
        if self.contains(mouseX, mouseY):
            # a click on the popover background just moves focus off a box
            self.commit(graph)
            self.cancelEdit()
            return True
        # clicking away closes it, and swallows the click so that dismissing
        # the popover never also drops a point onto the graph
        self.close(graph)
        return True

    def handleKey(self, key, graph):
        if not self.isOpen:
            return False
        if key == 'escape':
            self.close(graph)
        elif self.editIndex is None:
            return False
        elif key == 'backspace':
            self.buffer = self.buffer[:-1]
            self.errorMessage = ''
        elif key in ('enter', 'return'):
            if self.commit(graph):
                self.cancelEdit()
        elif key == 'tab':
            # tab walks the four boxes, which is how you would set a whole
            # window without touching the mouse
            if self.commit(graph):
                self.startEdit(graph, (self.editIndex + 1) % 4)
        elif len(key) == 1:
            self.buffer += key
            self.errorMessage = ''
        else:
            return False
        return True

    # ---------- drawing ----------

    def draw(self, graph):
        self.toggleButton.draw(pressed=self.isOpen)
        if not self.isOpen:
            return

        drawRect(self.left, self.top, self.width, self.height,
                 fill=panelFill, border=panelBorder)
        for index in range(4):
            self.drawBox(graph, index)

        # the comparison signs, centred between each pair of boxes
        signLeft = self.left + WindowControls.padding + WindowControls.boxWidth
        for row in range(2):
            name = 'x' if row == 0 else 'y'
            middle = self.boxTop(row * 2) + WindowControls.boxHeight / 2
            drawLabel(f'< {name} <', signLeft + WindowControls.signWidth / 2,
                      middle, size=12, bold=True)

        if self.errorMessage != '':
            drawLabel(self.errorMessage, self.left + WindowControls.padding,
                      self.top + self.height - 4, size=9, align='left',
                      fill=errorColor)
        else:
            drawLabel('tab moves on, enter applies, esc closes',
                      self.left + WindowControls.padding,
                      self.top + self.height - 4, size=9, align='left',
                      fill=mutedColor)

    def drawBox(self, graph, index):
        left, top = self.boxLeft(index), self.boxTop(index)
        editing = (index == self.editIndex)
        drawRect(left, top, WindowControls.boxWidth, WindowControls.boxHeight,
                 fill=editFill if editing else 'white',
                 border=errorColor if (editing and self.errorMessage != '')
                        else panelBorder)
        if editing:
            text = self.buffer + '|'
        else:
            text = self.currentText(graph, index)
        drawLabel(text, left + 5, top + WindowControls.boxHeight / 2,
                  size=11, align='left')
########################################################################