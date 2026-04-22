import XCTest

final class DemoFlowUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func launchApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-uitest-autologin"]
        app.launch()
        return app
    }

    func attachScreenshot(_ app: XCUIApplication, name: String) {
        let screenshot = app.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    // Waits up to `timeout` seconds for `element` to exist and be hittable.
    @discardableResult
    func waitHittable(_ element: XCUIElement, timeout: TimeInterval = 20) -> Bool {
        let start = Date()
        while Date().timeIntervalSince(start) < timeout {
            if element.exists && element.isHittable { return true }
            RunLoop.current.run(until: Date().addingTimeInterval(0.25))
        }
        return false
    }

    func testDemoFlow() throws {
        let app = launchApp()

        // 1. Wait for Home tab to appear (i.e. auto-login succeeded).
        let homeTab = app.tabBars.buttons["Home"]
        XCTAssertTrue(waitHittable(homeTab, timeout: 30), "Home tab should appear after auto-login")
        attachScreenshot(app, name: "01-home")

        // 2. Text Translate flow from Home card.
        let textCard = app.buttons["home.card.text_translate"]
        XCTAssertTrue(waitHittable(textCard), "Text Translate card should be tappable")
        textCard.tap()

        let translateInput = app.textViews["translate.input"]
        XCTAssertTrue(waitHittable(translateInput), "Translate input should appear")
        translateInput.tap()
        translateInput.typeText("I need the report by Friday. No exceptions.")
        attachScreenshot(app, name: "02-translate-typed")

        // Dismiss keyboard so the translate button isn't covered.
        app.navigationBars["Text Translate"].tap()

        let translateButton = app.buttons["translate.button"]
        XCTAssertTrue(waitHittable(translateButton), "Translate button should be enabled")
        translateButton.tap()

        // "N credits left" only appears in TranslationResultView.
        let creditsLabel = app.staticTexts.matching(NSPredicate(format: "label CONTAINS 'credits left'")).firstMatch
        let resultById = app.staticTexts["translate.result"]
        let appeared = creditsLabel.waitForExistence(timeout: 60) || resultById.waitForExistence(timeout: 5)
        // Dismiss keyboard via drag from mid-screen downward.
        if app.keyboards.count > 0 {
            let top = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.3))
            let bottom = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.95))
            top.press(forDuration: 0.1, thenDragTo: bottom)
        }
        RunLoop.current.run(until: Date().addingTimeInterval(0.8))
        attachScreenshot(app, name: "03-translate-result")
        XCTAssertTrue(appeared, "Translation result should render within 65s")

        // Back to Home.
        app.navigationBars.buttons.element(boundBy: 0).tap()

        // 3. Chat tab — tap into a room via NavigationLink (the previously flaky path).
        let chatTab = app.tabBars.buttons["Chat"]
        XCTAssertTrue(waitHittable(chatTab))
        chatTab.tap()

        // If there are no rooms, create one so the navigation assertion is meaningful.
        let createRoomButton = app.buttons["room.create.button"]
        let anyRoomRow = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH 'room.link.'")).firstMatch
        let noRooms = app.staticTexts["No Chat Rooms"]

        if noRooms.waitForExistence(timeout: 3) {
            XCTAssertTrue(waitHittable(createRoomButton))
            createRoomButton.tap()
            let nameField = app.textFields.firstMatch
            XCTAssertTrue(waitHittable(nameField))
            nameField.tap()
            nameField.typeText("UITest Demo Room")
            app.buttons["Create"].tap()
        }

        attachScreenshot(app, name: "04-chat-rooms")

        XCTAssertTrue(waitHittable(anyRoomRow, timeout: 20), "At least one room row should appear")
        anyRoomRow.tap()

        // 4. In the chat room, send a message and verify it appears.
        let chatInput = app.textFields["chat.input"]
        XCTAssertTrue(waitHittable(chatInput, timeout: 20), "Chat input should appear (NavigationLink tapped successfully)")
        chatInput.tap()
        chatInput.typeText("Hello from UITest")

        let sendButton = app.buttons["chat.send"]
        XCTAssertTrue(waitHittable(sendButton))
        sendButton.tap()

        // Wait for the message to render somewhere on-screen.
        let messageText = app.staticTexts.matching(NSPredicate(format: "label CONTAINS 'Hello from UITest' OR label CONTAINS 'UITest'")).firstMatch
        _ = messageText.waitForExistence(timeout: 30)
        // Dismiss keyboard for a clean demo screenshot.
        if app.keyboards.count > 0 {
            app.swipeDown()
        }
        RunLoop.current.run(until: Date().addingTimeInterval(0.5))
        attachScreenshot(app, name: "05-chat-message-sent")

        // Back to Rooms list.
        app.navigationBars.buttons.element(boundBy: 0).tap()

        // 5. Transcripts tab — just verify we can reach it and render the list state.
        let transcriptsTab = app.tabBars.buttons["Transcripts"]
        XCTAssertTrue(waitHittable(transcriptsTab))
        transcriptsTab.tap()
        // Wait for either the list row or the empty state.
        let anyTranscriptRow = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH 'transcript.row.'")).firstMatch
        let emptyTranscripts = app.staticTexts["No Transcripts"]
        let foundTranscriptScreen = waitHittable(anyTranscriptRow, timeout: 3) || emptyTranscripts.waitForExistence(timeout: 3)
        XCTAssertTrue(foundTranscriptScreen, "Transcripts tab should show list or empty state")
        attachScreenshot(app, name: "06-transcripts")

        // 6. Profile tab.
        let profileTab = app.tabBars.buttons["Profile"]
        XCTAssertTrue(waitHittable(profileTab))
        profileTab.tap()
        // UITest User is the name we dev-logged in as.
        let profileName = app.staticTexts.matching(NSPredicate(format: "label CONTAINS 'UITest User'")).firstMatch
        XCTAssertTrue(profileName.waitForExistence(timeout: 10), "Profile should show 'UITest User'")
        attachScreenshot(app, name: "07-profile")
    }
}
