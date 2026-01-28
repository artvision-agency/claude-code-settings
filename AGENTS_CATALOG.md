# Каталог агентов Claude Code

> Быстрый справочник: какого агента вызвать для какой задачи.
> Обновлено: 2026-01-28

## Как вызвать агента

```
# Автоматически (Claude сам выберет)
Task tool → subagent_type = "agent-name"

# Вручную попросить
"Используй frontend-developer агента для этой задачи"
```

---

## 🎯 Разработка (по языкам/фреймворкам)

| Задача | Агент |
|--------|-------|
| **Frontend/React** | `react-specialist`, `nextjs-developer`, `frontend-developer` |
| **Vue.js** | `vue-expert` |
| **Angular** | `angular-architect` |
| **Backend Python** | `python-pro`, `django-pro`, `fastapi-pro` |
| **Backend Node.js** | `javascript-pro`, `typescript-pro` |
| **Go** | `golang-pro` |
| **Rust** | `rust-pro` |
| **PHP/Laravel** | `php-pro`, `laravel-specialist` |
| **Java/Spring** | `java-pro`, `java-architect`, `spring-boot-engineer` |
| **C#/.NET** | `csharp-pro`, `dotnet-core-expert`, `dotnet-architect` |
| **C/C++** | `c-pro`, `cpp-pro` |
| **Ruby/Rails** | `ruby-pro`, `rails-expert` |
| **Elixir** | `elixir-pro` |
| **Swift/iOS** | `swift-expert`, `ios-developer` |
| **Kotlin/Android** | `kotlin-specialist` |
| **Flutter** | `flutter-expert` |
| **Mobile общее** | `mobile-developer` |

---

## 🏗️ Архитектура и инфраструктура

| Задача | Агент |
|--------|-------|
| **Ревью архитектуры** | `architect-reviewer` |
| **Backend архитектура** | `backend-architect` |
| **Микросервисы** | `microservices-architect` |
| **API дизайн** | `api-designer`, `graphql-architect` |
| **Базы данных** | `database-architect`, `database-administrator`, `database-optimizer`, `postgres-pro`, `sql-pro` |
| **DevOps/CI-CD** | `devops-engineer`, `deployment-engineer` |
| **Kubernetes** | `kubernetes-specialist`, `kubernetes-architect` |
| **Terraform/IaC** | `terraform-specialist` |
| **Cloud (AWS/Azure/GCP)** | `cloud-architect`, `azure-infra-engineer`, `hybrid-cloud-architect` |
| **SRE/Reliability** | `sre-engineer`, `observability-engineer` |

---

## 🔒 Безопасность

| Задача | Агент |
|--------|-------|
| **Security аудит кода** | `security-auditor` |
| **Пентест** | `penetration-tester` |
| **Security инфраструктуры** | `security-engineer` |
| **Инцидент-респонс** | `incident-responder`, `devops-incident-responder` |
| **Compliance** | `compliance-auditor` |
| **Frontend security** | `frontend-security-coder` |
| **Backend security** | `backend-security-coder` |
| **Mobile security** | `mobile-security-coder` |
| **AD Security** | `ad-security-reviewer` |
| **Reverse engineering** | `reverse-engineer` |

---

## 📊 Data & AI/ML

| Задача | Агент |
|--------|-------|
| **Data Engineering** | `data-engineer` |
| **Data Science** | `data-scientist` |
| **Data Analysis** | `data-analyst` |
| **ML Engineering** | `ml-engineer`, `machine-learning-engineer` |
| **MLOps** | `mlops-engineer` |
| **NLP** | `nlp-engineer` |
| **LLM/Prompt** | `llm-architect`, `prompt-engineer` |
| **AI интеграции** | `ai-engineer` |
| **Vector DB** | `vector-database-engineer` |
| **Quant/Trading** | `quant-analyst` |

---

## 🔧 Quality & Testing

| Задача | Агент |
|--------|-------|
| **Code Review** | `code-reviewer` |
| **QA/Testing** | `qa-expert`, `test-automator` |
| **TDD** | `tdd-orchestrator` |
| **Performance** | `performance-engineer` |
| **Debugging** | `debugger`, `error-detective` |
| **Accessibility** | `accessibility-tester` |
| **Рефакторинг** | `refactoring-specialist` |

---

## 📝 Документация и контент

| Задача | Агент |
|--------|-------|
| **Техническая документация** | `technical-writer`, `documentation-engineer` |
| **API документация** | `api-documenter` |
| **Туториалы** | `tutorial-engineer` |
| **Reference guides** | `reference-builder`, `docs-architect` |
| **Диаграммы** | `mermaid-expert` |
| **C4 документация** | `c4-context` |

---

## 🌐 SEO и маркетинг

| Задача | Агент |
|--------|-------|
| **SEO аудит** | `seo-analyzer` |
| **SEO стратегия** | `seo-specialist` |
| **Контент-маркетинг** | `content-marketer` |
| **Лендинги** | `landing-page-agent` |
| **Sales** | `sales-engineer`, `sales-automator` |

---

## 💼 Бизнес и продукт

| Задача | Агент |
|--------|-------|
| **Product Management** | `product-manager` |
| **Project Management** | `project-manager`, `scrum-master` |
| **Business Analysis** | `business-analyst` |
| **UX Research** | `ux-researcher` |
| **UI/UX Design** | `ui-designer`, `ui-ux-designer` |
| **Market Research** | `market-researcher`, `competitive-analyst` |
| **Стартапы** | `startup-analyst` |
| **Legal** | `legal-advisor` |
| **HR** | `hr-pro` |
| **Финтех** | `fintech-engineer` |
| **Блокчейн** | `blockchain-developer` |

---

## 🛠️ Специализированные

| Задача | Агент |
|--------|-------|
| **CLI разработка** | `cli-developer` |
| **Electron apps** | `electron-pro` |
| **WebSocket/Realtime** | `websocket-engineer` |
| **IoT** | `iot-engineer` |
| **Embedded** | `embedded-systems` |
| **Game Dev** | `game-developer` |
| **MCP серверы** | `mcp-developer` |
| **Slack боты** | `slack-expert` |
| **WordPress** | `wordpress-master` |
| **Payment интеграции** | `payment-integration` |

---

## 🔄 Мета/Оркестрация

| Задача | Агент |
|--------|-------|
| **Координация агентов** | `multi-agent-coordinator` |
| **Workflow** | `workflow-orchestrator` |
| **Task distribution** | `task-distributor` |
| **Git workflow** | `git-workflow-manager` |
| **Dependencies** | `dependency-manager` |
| **Sysadmin** | `sysadmin-orchestrator` |
| **IT Ops** | `it-ops-orchestrator` |
| **Token оптимизация** | `token-guardian` |

---

## 💡 Подсказки

1. **Не знаешь какой агент** → просто опиши задачу, Claude подберёт
2. **Нужен конкретный** → "используй `agent-name` для этого"
3. **Комплексная задача** → несколько агентов последовательно
4. **Проверить результат** → `code-reviewer`, `architect-reviewer`

---

*Полный список встроенных: см. Task tool в системе*
*Кастомные: `ls ~/.claude/agents/`*
*Бэкап удалённых: `~/.claude/agents-backup-20260128-221346/`*
