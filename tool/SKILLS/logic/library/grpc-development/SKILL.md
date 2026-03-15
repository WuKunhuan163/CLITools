---
name: grpc-development
description: gRPC service development patterns. Use when working with grpc development concepts or setting up related projects.
---

# gRPC Development

## Core Concepts

- **Protocol Buffers**: Schema-first, binary serialization
- **Service Definition**: RPC methods defined in `.proto` files
- **Streaming**: Unary, server-streaming, client-streaming, bidirectional
- **Code Generation**: Generate client/server stubs from `.proto`

## Proto Definition
```protobuf
syntax = "proto3";
package userservice;

service UserService {
  rpc GetUser (GetUserRequest) returns (User);
  rpc ListUsers (ListUsersRequest) returns (stream User);
}

message GetUserRequest { string id = 1; }
message User { string id = 1; string name = 2; string email = 3; }
```

## Python Server
```python
class UserServicer(user_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        user = db.find_user(request.id)
        if not user:
            context.abort(grpc.StatusCode.NOT_FOUND, "User not found")
        return user_pb2.User(id=user.id, name=user.name)
```

## When to Use gRPC
- Internal service-to-service communication
- Low latency, high throughput requirements
- Strongly typed contracts needed
- Bidirectional streaming

## When to Prefer REST
- Public APIs (browser compatibility)
- Simple CRUD operations
- Human-readable debugging needed
