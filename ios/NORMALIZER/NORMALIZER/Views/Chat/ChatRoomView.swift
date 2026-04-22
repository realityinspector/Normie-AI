import SwiftUI

struct ChatRoomView: View {
    @State private var vm: ChatRoomViewModel
    @Environment(AuthViewModel.self) private var authVM
    @State private var showTranscriptAlert = false

    init(roomId: UUID) {
        _vm = State(initialValue: ChatRoomViewModel(roomId: roomId))
    }

    var body: some View {
        VStack(spacing: 0) {
            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(vm.messages) { message in
                            MessageBubbleView(
                                message: message,
                                isFromCurrentUser: message.senderId == authVM.currentUser?.id
                            )
                            .id(message.id)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 8)
                }
                .onChange(of: vm.messages.count) { _, _ in
                    withAnimation {
                        if let lastId = vm.messages.last?.id {
                            proxy.scrollTo(lastId, anchor: .bottom)
                        }
                    }
                }
            }

            Divider()

            // Input bar
            HStack(spacing: 12) {
                TextField("Type a message...", text: $vm.inputText)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityIdentifier("chat.input")
                    .onSubmit {
                        Task { await vm.sendMessage() }
                    }

                Button {
                    Task { await vm.sendMessage() }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.title2)
                }
                .disabled(vm.inputText.trimmingCharacters(in: .whitespaces).isEmpty || vm.isSending)
                .accessibilityIdentifier("chat.send")
            }
            .padding()
        }
        .navigationTitle(vm.room?.name ?? "Chat")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showTranscriptAlert = true
                } label: {
                    Image(systemName: "square.and.arrow.down")
                }
            }
        }
        .alert("Save Transcript", isPresented: $showTranscriptAlert) {
            Button("Save") {
                Task {
                    let saved = await vm.saveTranscript()
                    if saved {
                        // Show success feedback
                    }
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Save this conversation as a transcript?")
        }
        .task {
            await vm.load()
        }
        .onDisappear {
            Task { await vm.disconnect() }
        }
    }
}
