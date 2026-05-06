workspace {
    model {
        # Actors
        user = person "User" "A person who wants to register and activate their account" {
            tags "External"
        }

        # External systems
        emailService = softwareSystem "Email Service" "SMTP server or email provider that delivers verification emails to users" {
            tags "External"
        }

        # User Registration API system
        registrationApi = softwareSystem "User Registration API" "Handles user registration and account activation via email verification" {

            apiApp = container "FastAPI Application" "Handles HTTP requests and orchestrates the registration flow" "Python / FastAPI" {

                registrationRouter = component "Registration Router" "Exposes POST /auth/register to create a new unactivated user account" "FastAPI APIRouter"
                activationRouter = component "Activation Router" "Exposes POST /auth/activate, protected by HTTP Basic Auth, to activate a user account" "FastAPI APIRouter"

                userService = component "User Service" "Orchestrates user creation and account activation business logic" "Python Service"
                verificationService = component "Verification Service" "Generates 4-digit codes, stores them with 1-minute TTL, and validates them at activation" "Python Service"
                emailNotificationService = component "Email Notification Service" "Builds and sends verification emails containing the 4-digit code" "Python Service"

                userRepository = component "User Repository" "Reads and writes user records from the database" "SQLAlchemy / asyncpg"
                verificationRepository = component "Verification Repository" "Stores and retrieves verification codes with expiry timestamp in the database" "SQLAlchemy / asyncpg"
            }

            database = container "Database" "Stores user accounts with hashed passwords and activation status" "PostgreSQL" {
                tags "Database"
            }

        }

        # Relationships (Actors -> System)
        user -> registrationApi "Registers and activates account using" "HTTPS / JSON"

        # Relationships (Actors -> Containers)
        user -> apiApp "Sends HTTP requests to" "HTTPS / JSON"

        # Relationships (Containers)
        apiApp -> database "Reads from and writes to" "asyncpg"
        apiApp -> emailService "Sends transactional verification emails via" "SMTP / HTTP"

        # Relationships (Components)
        registrationRouter -> userService "Delegates user creation to"
        activationRouter -> userService "Delegates account activation to"
        userService -> verificationService "Generates and validates 4-digit codes using"
        userService -> emailNotificationService "Requests verification email dispatch"
        userService -> userRepository "Persists and retrieves user data"
        verificationService -> verificationRepository "Stores and retrieves verification codes"
        userRepository -> database "Reads from and writes to" "asyncpg"
        verificationRepository -> database "Reads from and writes to" "asyncpg"
        emailNotificationService -> emailService "Sends email via" "SMTP / HTTP"

        # Local deployment environment
        local = deploymentEnvironment "Local" {
            deploymentNode "Developer Machine" {

                deploymentNode "uvicorn" "ASGI server" {
                    apiAppLocalInstance = containerInstance apiApp
                }

                deploymentNode "Docker Compose" {

                    deploymentNode "PostgreSQL 18" {
                        databaseLocalInstance = containerInstance database
                    }

                    deploymentNode "Mailpit" "SMTP server mock" {
                        emailServiceLocalInstance = softwareSystemInstance emailService
                    }
                }
            }
        }
    }

    views {
        systemContext registrationApi "SystemContextView" {
            include *
            autoLayout lr
        }

        container registrationApi "ContainerView" {
            include *
            autoLayout lr
        }

        component apiApp "ComponentView" {
            include *
            autoLayout lr
        }

        deployment registrationApi "Local" "LocalDeploymentView" {
            include *
            autoLayout lr
        }

        styles {
            element "External" {
                background #d3d3d3
            }
            element "Person" {
                shape Person
            }
            element "Database" {
                shape Cylinder
                height 250
                width 300
            }
        }
    }
}
