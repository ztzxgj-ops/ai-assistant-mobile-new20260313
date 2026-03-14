import SwiftUI

@main
struct AIAssistantApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.hiddenTitleBar)
    }
}

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var isLoggedIn = false
    @State private var username = ""
    @State private var password = ""

    var body: some View {
        if isLoggedIn {
            TabView(selection: $selectedTab) {
                ChatView()
                    .tabItem {
                        Label("聊天", systemImage: "bubble.left.and.bubble.right")
                    }
                    .tag(0)

                PlansView()
                    .tabItem {
                        Label("计划", systemImage: "checklist")
                    }
                    .tag(1)

                RemindersView()
                    .tabItem {
                        Label("提醒", systemImage: "bell")
                    }
                    .tag(2)

                SettingsView(isLoggedIn: $isLoggedIn)
                    .tabItem {
                        Label("设置", systemImage: "gear")
                    }
                    .tag(3)
            }
            .frame(minWidth: 900, minHeight: 700)
        } else {
            LoginView(isLoggedIn: $isLoggedIn, username: $username, password: $password)
        }
    }
}

// MARK: - 登录视图

struct LoginView: View {
    @Binding var isLoggedIn: Bool
    @Binding var username: String
    @Binding var password: String
    @State private var showRegister = false

    var body: some View {
        VStack(spacing: 30) {
            VStack(spacing: 10) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 60))
                    .foregroundColor(.blue)

                Text("AI 个人助理")
                    .font(.system(size: 32, weight: .bold))
                    .foregroundColor(.primary)

                Text("macOS 版")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            VStack(spacing: 15) {
                TextField("用户名", text: $username)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 300)

                SecureField("密码", text: $password)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 300)
            }

            HStack(spacing: 15) {
                Button(action: {
                    // 模拟登录
                    if !username.isEmpty && !password.isEmpty {
                        isLoggedIn = true
                    }
                }) {
                    Text("登录")
                        .frame(width: 100)
                        .padding(8)
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(6)
                }

                Button(action: {
                    showRegister = true
                }) {
                    Text("注册")
                        .frame(width: 100)
                        .padding(8)
                        .background(Color.gray.opacity(0.2))
                        .foregroundColor(.primary)
                        .cornerRadius(6)
                }
            }

            Text("演示账户: demo / demo123")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(50)
        .frame(width: 500, height: 500)
    }
}

// MARK: - 聊天视图

struct ChatView: View {
    @State private var messages: [ChatMessage] = [
        ChatMessage(id: "1", role: "assistant", content: "你好！我是 AI 助理，很高兴认识你。有什么我可以帮助的吗？", timestamp: Date())
    ]
    @State private var messageText = ""

    var body: some View {
        VStack(spacing: 0) {
            // 标题
            VStack {
                Text("AI 聊天")
                    .font(.title2)
                    .fontWeight(.bold)
                Divider()
            }
            .padding()

            // 消息列表
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(messages) { message in
                            HStack {
                                if message.role == "user" {
                                    Spacer()
                                    Text(message.content)
                                        .padding(12)
                                        .background(Color.blue)
                                        .foregroundColor(.white)
                                        .cornerRadius(8)
                                        .frame(maxWidth: 500, alignment: .trailing)
                                } else {
                                    Text(message.content)
                                        .padding(12)
                                        .background(Color.gray.opacity(0.2))
                                        .cornerRadius(8)
                                        .frame(maxWidth: 500, alignment: .leading)
                                    Spacer()
                                }
                            }
                            .id(message.id)
                        }
                    }
                    .padding()
                }
                .onChange(of: messages.count) { _ in
                    if let lastMessage = messages.last {
                        proxy.scrollTo(lastMessage.id, anchor: .bottom)
                    }
                }
            }

            Divider()

            // 输入框
            HStack(spacing: 10) {
                TextField("输入消息...", text: $messageText)
                    .textFieldStyle(.roundedBorder)

                Button(action: {
                    if !messageText.isEmpty {
                        let userMessage = ChatMessage(id: UUID().uuidString, role: "user", content: messageText, timestamp: Date())
                        messages.append(userMessage)

                        // 模拟 AI 回复
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                            let aiMessage = ChatMessage(id: UUID().uuidString, role: "assistant", content: "我已收到你的消息：\(messageText)", timestamp: Date())
                            messages.append(aiMessage)
                        }

                        messageText = ""
                    }
                }) {
                    Image(systemName: "paperplane.fill")
                        .foregroundColor(.blue)
                }
                .buttonStyle(.plain)
            }
            .padding()
        }
    }
}

// MARK: - 计划视图

struct PlansView: View {
    @State private var plans: [WorkPlan] = [
        WorkPlan(id: "1", title: "完成项目文档", priority: "high", status: "pending", dueDate: "2026-03-15"),
        WorkPlan(id: "2", title: "代码审查", priority: "medium", status: "pending", dueDate: "2026-03-16"),
        WorkPlan(id: "3", title: "修复 bug", priority: "high", status: "completed", dueDate: "2026-03-14")
    ]
    @State private var newPlanTitle = ""
    @State private var showAddPlan = false

    var body: some View {
        VStack(spacing: 0) {
            // 标题
            VStack {
                HStack {
                    Text("工作计划")
                        .font(.title2)
                        .fontWeight(.bold)
                    Spacer()
                    Button(action: { showAddPlan = true }) {
                        Image(systemName: "plus.circle.fill")
                            .foregroundColor(.blue)
                    }
                    .buttonStyle(.plain)
                }
                Divider()
            }
            .padding()

            // 计划列表
            List(plans) { plan in
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text(plan.title)
                            .fontWeight(.bold)
                        Spacer()
                        Text(plan.status)
                            .font(.caption)
                            .padding(4)
                            .background(plan.status == "completed" ? Color.green.opacity(0.2) : Color.orange.opacity(0.2))
                            .cornerRadius(4)
                    }

                    HStack(spacing: 12) {
                        Label(plan.priority, systemImage: "flag.fill")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        Label(plan.dueDate, systemImage: "calendar")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
        }
    }
}

// MARK: - 提醒视图

struct RemindersView: View {
    @State private var reminders: [Reminder] = [
        Reminder(id: "1", content: "下午 3 点开会", remindTime: "2026-03-13 15:00"),
        Reminder(id: "2", content: "提交报告", remindTime: "2026-03-14 09:00"),
        Reminder(id: "3", content: "健身房", remindTime: "2026-03-13 18:00")
    ]

    var body: some View {
        VStack(spacing: 0) {
            // 标题
            VStack {
                Text("提醒")
                    .font(.title2)
                    .fontWeight(.bold)
                Divider()
            }
            .padding()

            // 提醒列表
            List(reminders) { reminder in
                VStack(alignment: .leading, spacing: 4) {
                    Text(reminder.content)
                        .fontWeight(.bold)
                    Text(reminder.remindTime)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
    }
}

// MARK: - 设置视图

struct SettingsView: View {
    @Binding var isLoggedIn: Bool
    @State private var storageMode = "cloud"

    var body: some View {
        VStack(spacing: 0) {
            // 标题
            VStack {
                Text("设置")
                    .font(.title2)
                    .fontWeight(.bold)
                Divider()
            }
            .padding()

            Form {
                Section("账户") {
                    HStack {
                        Text("用户名")
                        Spacer()
                        Text("demo")
                            .foregroundColor(.secondary)
                    }

                    HStack {
                        Text("邮箱")
                        Spacer()
                        Text("demo@example.com")
                            .foregroundColor(.secondary)
                    }
                }

                Section("存储模式") {
                    Picker("模式", selection: $storageMode) {
                        Text("云端模式").tag("cloud")
                        Text("本地模式").tag("local")
                    }
                    .pickerStyle(.segmented)

                    if storageMode == "cloud" {
                        Text("数据将同步到云端服务器")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    } else {
                        Text("数据仅保存在本地，不会同步")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Section("关于") {
                    HStack {
                        Text("应用版本")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }

                    HStack {
                        Text("服务器")
                        Spacer()
                        Text("47.109.148.176")
                            .foregroundColor(.secondary)
                            .font(.caption)
                    }
                }

                Section {
                    Button(action: {
                        isLoggedIn = false
                    }) {
                        HStack {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                            Text("退出登录")
                        }
                        .foregroundColor(.red)
                    }
                }
            }
            .padding()
        }
    }
}

// MARK: - 数据模型

struct ChatMessage: Identifiable {
    let id: String
    let role: String
    let content: String
    let timestamp: Date
}

struct WorkPlan: Identifiable {
    let id: String
    let title: String
    let priority: String
    let status: String
    let dueDate: String
}

struct Reminder: Identifiable {
    let id: String
    let content: String
    let remindTime: String
}

#Preview {
    ContentView()
}
