from cmu_graphics import *
import dataset

panelFill = rgb(255, 255, 255)
panelBorder = rgb(205, 205, 205)
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


# 3.0 -> '3', 2.5 -> '2.5', 1/3 -> '0.3333'
def formatCell(value):
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

    def draw(self, enabled = True, pressed = False):
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

    # (index, top, totalHeight) for every result
    def rowLayout(self, analysisEngine):
        layout = []
        top = self.panel.contentTop() + 6
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

    def draw(self, analysisEngine, colorForResult, tieMessage = ''):
        if len(analysisEngine.results) == 0:
            drawLabel('No model fitted yet.', self.left,
                      self.panel.contentTop() + 16, size=11, align='left',
                      fill=mutedColor)
            drawLabel('Add at least 2 points.', self.left,
                      self.panel.contentTop() + 32, size=11, align='left',
                      fill=mutedColor)
            return

        bottom = self.panel.bottom - 8
        for index, top, height in self.rowLayout(analysisEngine):
            if top > bottom:
                break
            result = analysisEngine.results[index]
            self.drawRow(result, index, top, colorForResult(result))
            if index == self.expandedIndex:
                self.drawDetail(result, top + ModelCards.rowHeight)

        self.drawFooter(analysisEngine, tieMessage)

    def drawRow(self, result, index, top, color):
        middle = top + ModelCards.rowHeight / 2
        if index == self.expandedIndex:
            drawRect(self.left - 4, top, self.width + 8,
                     ModelCards.rowHeight, fill=selectFill)

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
            drawRect(self.left + 16, y - 4, barWidth * result.akaikeWeight, 8,
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

    def drawFooter(self, analysisEngine, tieMessage):
        y = self.panel.bottom - 12
        for name, reason in analysisEngine.unavailable:
            drawLabel(f'{name}: {reason}'[:48], self.left, y, size=9,
                      align='left', fill=mutedColor)
            y -= 11
        if len(analysisEngine.unavailable) > 0:
            drawLabel('not fitted', self.left, y, size=9, align='left',
                      bold=True, fill=mutedColor)
            y -= 14
        if tieMessage != '':
            for line in reversed(wrapText(tieMessage, ModelCards.wrapWidth)):
                drawLabel(line, self.left, y, size=9, align='left')
                y -= 10
            drawLabel('too close to call', self.left, y, size=9,
                      align='left', bold=True)
    ########################################################################